"""Studio renders and turntable animations of the printed parts.

Run headless so the output is reproducible and can be regenerated after a
design change, instead of being screenshotted once in week three and quietly
going stale:

    make renders            # four stills
    make animation          # turntable and fit animations
    make renders SAMPLES=256 THEME=light

OpenSCAD's own previews are for checking geometry while working, and every
geometry test in `tests/` uses them. These are for the poster, the report and
the deck, where flat shading reads as unfinished.

Blender's Python API moves between major versions, so anything version
sensitive here — the STL importer's name, GPU backend — is wrapped and falls
back rather than aborting the render.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

# STL carries no units; OpenSCAD wrote millimetres. Cycles is physically based,
# so working in metres keeps light energies in a sane range.
MM = 0.001

BUILD = Path(__file__).resolve().parents[1] / "build"
OUT = BUILD / "renders"

# Purdue old gold on charcoal. The team presents this at Purdue, so the parts
# may as well be in the university's colours on a poster board.
#
# Base colours are deliberately low. Cycles is physically based and these are
# lit hard: an 0.8 albedo under a key light clips to white and every part in
# the shot turns into the same pale blob. These are the values that read as
# coloured plastic after AgX tone mapping, not what the filament looks like in
# your hand.
THEMES = {
    "dark": {
        "frame": (0.340, 0.235, 0.080, 1.0),
        "head": (0.022, 0.023, 0.026, 1.0),
        "holder": (0.340, 0.235, 0.080, 1.0),
        "puck": (0.015, 0.016, 0.019, 1.0),
        "pod": (0.040, 0.044, 0.052, 1.0),
        "backdrop": (0.013, 0.014, 0.017, 1.0),
        "world": (0.022, 0.024, 0.030, 1.0),
    },
    "light": {
        "frame": (0.300, 0.205, 0.068, 1.0),
        "head": (0.300, 0.300, 0.305, 1.0),
        "holder": (0.300, 0.205, 0.068, 1.0),
        "puck": (0.040, 0.042, 0.048, 1.0),
        "pod": (0.120, 0.125, 0.135, 1.0),
        "backdrop": (0.520, 0.522, 0.530, 1.0),
        "world": (0.180, 0.185, 0.195, 1.0),
    },
}

PALETTE: dict[str, tuple] = {}


def main() -> None:
    args = parse_args()
    PALETTE.update(THEMES[args.theme])
    OUT.mkdir(parents=True, exist_ok=True)

    if args.mode in ("stills", "all"):
        for name in ("hero", "frame", "montage", "parts"):
            reset_scene()
            configure_render(args.samples)
            objects, centre, radius = build(name)
            studio(radius)
            render_still(OUT / f"{name}.png")
            print(f"rendered {name}")

    if args.mode == "turntable":
        reset_scene()
        configure_render(args.anim_samples)
        objects, centre, radius = build("hero")
        studio(radius)
        turntable(objects, centre, args.frames)
        render_animation(OUT / "turntable.mp4")
        print("rendered turntable")

    if args.mode == "fit":
        reset_scene()
        configure_render(args.anim_samples)
        objects, centre, radius = build("fit")
        studio(radius)
        render_animation(OUT / "fit.mp4")
        print("rendered fit")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="blender_render")
    # One animation per invocation. Rendering two FFmpeg outputs from a single
    # Blender session leaves the second file an empty container.
    parser.add_argument("--mode", default="stills", choices=("stills", "turntable", "fit"))
    parser.add_argument("--theme", default="dark", choices=tuple(THEMES))
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--anim-samples", type=int, default=48)
    parser.add_argument("--frames", type=int, default=96)
    return parser.parse_args(argv)


# --- Shots ------------------------------------------------------------------
# In the head model +y is the nose, so azimuth 90 looks the subject in the face
# and 270 is directly behind.


def build(name: str):
    if name == "hero":
        parts = [load("cap_frame.stl", "frame"), load("head_form.stl", "head")]
        centre, radius = frame_shot(parts, azimuth=55, elevation=20)
    elif name == "frame":
        parts = [load("cap_frame.stl", "frame")]
        centre, radius = frame_shot(parts, azimuth=235, elevation=24)
    elif name == "montage":
        parts = [load("cap_frame.stl", "frame")]
        centre, radius = frame_shot(parts, azimuth=90, elevation=88, margin=1.10)
    elif name == "parts":
        parts = [
            load("electrode_holder.stl", "holder"),
            load("sensor_puck.stl", "puck"),
            load("pod_base.stl", "pod"),
            load("pod_lid.stl", "pod"),
        ]
        arrange_in_row(parts, gap=0.012)
        centre, radius = frame_shot(parts, azimuth=62, elevation=36, margin=1.12)
    elif name == "fit":
        cap, head = load("cap_frame.stl", "frame"), load("head_form.stl", "head")
        parts = [cap, head]
        # Lift first, then frame: the shot has to hold the frame at the top of
        # its travel, and framing it at rest crops the start of the move.
        radius = max((Vector(c) - bounds_centre(parts)).length for c in
                     [cc for o in parts for cc in world_corners(o)])
        cap.location = (0, 0, radius * 0.55)
        bpy.context.view_layer.update()
        centre, radius = frame_shot(parts, azimuth=55, elevation=14, margin=1.08)
        lower_onto_head(cap, radius * 0.55)
    else:
        raise SystemExit(f"unknown shot {name}")
    return parts, centre, radius


# --- Animation --------------------------------------------------------------


def turntable(objects, centre: Vector, frames: int) -> None:
    """Spin the subject under fixed lights for a seamless loop.

    The subject turns rather than the camera. With a moving camera the key
    light stays in the same place relative to the subject and the surface never
    changes, which reads as a still image that happens to be sliding around.
    Turning the subject walks the highlight across every curve, which is what
    makes the form legible.
    """
    pivot = bpy.data.objects.new("turntable", None)
    pivot.location = (centre.x, centre.y, 0.0)
    bpy.context.collection.objects.link(pivot)

    for obj in objects:
        obj.parent = pivot
        obj.matrix_parent_inverse = pivot.matrix_world.inverted()

    # The last frame is a duplicate of the first, so it is dropped from the
    # range: rendering both would stutter on every loop.
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (0, 0, 2 * math.pi)
    pivot.keyframe_insert("rotation_euler", frame=frames + 1)
    linear(pivot)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frames


def lower_onto_head(frame_obj, lift: float, frames: int = 72) -> None:
    """Settle the frame down onto the head form, then hold."""
    frame_obj.location = (0, 0, lift)
    frame_obj.keyframe_insert("location", frame=1)
    frame_obj.location = (0, 0, 0)
    frame_obj.keyframe_insert("location", frame=frames - 18)
    frame_obj.keyframe_insert("location", frame=frames)

    for curve in fcurves_of(frame_obj):
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.easing = "EASE_OUT"

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frames


def linear(obj) -> None:
    for curve in fcurves_of(obj):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"


def fcurves_of(obj) -> list:
    """Every F-curve driving this object, across Blender's two action layouts.

    Blender 4.4 moved keyframes out of `action.fcurves` and into slotted
    actions, where they live under layers, strips and a channelbag keyed by the
    object's action slot. Both spellings are handled so the script works on
    either side of that change.
    """
    animation = obj.animation_data
    if not animation or not animation.action:
        return []

    action = animation.action
    if hasattr(action, "fcurves"):
        return list(action.fcurves)

    slot = getattr(animation, "action_slot", None)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(slot) if slot else None
            if bag:
                curves.extend(bag.fcurves)
    return curves


# --- Scene construction -----------------------------------------------------


def load(filename: str, material: str):
    """Import one STL, scale it to metres, and give it a material."""
    path = BUILD / filename
    if not path.exists():
        raise SystemExit(f"missing {path} — run `make parts headform` first")

    before = set(bpy.data.objects)
    import_stl(path)
    imported = [o for o in bpy.data.objects if o not in before]
    if not imported:
        raise SystemExit(f"nothing imported from {path}")

    obj = imported[0]
    if len(imported) > 1:  # Some importers split by solid; join them back.
        bpy.ops.object.select_all(action="DESELECT")
        for o in imported:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.join()

    obj.scale = (MM, MM, MM)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    obj.data.materials.clear()
    obj.data.materials.append(plastic(material))
    shade_smooth(obj)
    return obj


def import_stl(path: Path) -> None:
    """Blender renamed the STL importer in 4.x; support both spellings."""
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        bpy.ops.import_mesh.stl(filepath=str(path))


def shade_smooth(obj) -> None:
    """Smooth the curved surfaces without rounding off the printed edges."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    if hasattr(bpy.ops.object, "shade_smooth_by_angle"):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    else:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(40)


def plastic(name: str):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing

    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = PALETTE[name]
    bsdf.inputs["Roughness"].default_value = 0.88 if name in ("head", "backdrop") else 0.40
    bsdf.inputs["Metallic"].default_value = 0.0
    return material


def studio(radius: float) -> None:
    """Three-point lighting inside a seamless backdrop, scaled to the subject."""
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = PALETTE["world"]
    background.inputs[1].default_value = 1.0

    cyclorama(radius)

    # Light falls off with the square of distance, and every light here is
    # placed at a multiple of the subject's radius, so power has to scale with
    # radius squared — otherwise small subjects render black and large ones
    # blow out.
    scale = radius**2
    # Large, high sources. Small lights close in light a disc of the backdrop
    # and leave a hard falloff edge arcing across the shot behind the subject,
    # which reads as a seam in the set rather than as lighting.
    key = add_area("key", (radius * 1.5, -radius * 1.4, radius * 2.4), radius * 3.0, 420 * scale)
    add_area("fill", (-radius * 2.0, -radius * 0.9, radius * 1.1), radius * 3.4, 110 * scale)
    add_area("rim", (-radius * 0.6, radius * 2.0, radius * 1.7), radius * 2.0, 260 * scale)
    key.data.shadow_soft_size = radius * 0.8


def cyclorama(radius: float) -> None:
    """A floor that curves up into a wall, revolved around the subject.

    A flat backdrop plane leaves its own edge in the picture as a hard horizon
    line cutting across the shot, however large the plane is made — the camera
    is close to floor level, so the edge always lands near the subject. A swept
    cove has no edge to see, and because it is a surface of revolution it works
    from any camera angle without being re-aimed.
    """
    # A long, shallow sweep that starts well outside the frame. At radius * 1.2
    # the floor barely cleared the subject and the wall rose immediately behind
    # it, putting a hard curved seam across the picture; the transition has to
    # be far enough away to read as a gradient rather than an edge.
    floor = radius * 5.0
    fillet = radius * 30.0
    height = radius * 60.0

    profile = [(0.0, 0.0, 0.0), (floor, 0.0, 0.0)]
    for step in range(1, 17):
        angle = math.radians(90) * step / 16
        profile.append((floor + fillet * math.sin(angle), 0.0, fillet * (1 - math.cos(angle))))
    profile.append((floor + fillet, 0.0, height))

    mesh = bpy.data.meshes.new("cyclorama")
    obj = bpy.data.objects.new("cyclorama", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new(point) for point in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(
        bm,
        geom=verts + edges,
        axis=(0, 0, 1),
        cent=(0, 0, 0),
        angle=2 * math.pi,
        steps=96,
        use_merge=True,
    )
    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(plastic("backdrop"))
    shade_smooth(obj)


def add_area(name: str, location, size: float, power: float):
    light = bpy.data.lights.new(name, type="AREA")
    light.size = size
    light.energy = power
    obj = bpy.data.objects.new(name, light)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    track_to(obj, Vector((0, 0, 0)))
    return obj


def frame_shot(objects, azimuth: float, elevation: float, margin: float = 1.06):
    """Point the camera at a set of objects and back off just far enough.

    Distance comes from projecting the subject's bounding box onto the camera's
    own axes, not from its bounding sphere. A bounding sphere around a dome is
    far larger than the dome, so sphere-based framing strands the subject in
    the middle of a mostly empty picture.

    Deriving it from the geometry rather than per-shot numbers means a design
    change that grows the frame cannot silently crop it out of the picture.
    """
    # Object transforms set through .location do not reach matrix_world until
    # the view layer is evaluated, and framing from stale matrices silently
    # crops whatever was moved.
    bpy.context.view_layer.update()

    centre = bounds_centre(objects)
    corners = [Vector(c) for obj in objects for c in world_corners(obj)]

    view = -_spherical(azimuth, elevation)
    right = view.cross(Vector((0, 0, 1)))
    right = right.normalized() if right.length > 1e-6 else Vector((1, 0, 0))
    up = right.cross(view).normalized()

    tan_h, tan_v = _half_fov_tans()
    needed = 0.0
    for corner in corners:
        offset = corner - centre
        depth = offset.dot(view)
        needed = max(
            needed,
            abs(offset.dot(right)) / tan_h - depth,
            abs(offset.dot(up)) / tan_v - depth,
        )

    radius = max((c - centre).length for c in corners)
    aim_camera(centre, azimuth, elevation, distance=needed * margin)
    return centre, radius


def _spherical(azimuth: float, elevation: float) -> Vector:
    az, el = math.radians(azimuth), math.radians(elevation)
    return Vector(
        (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    ).normalized()


def _half_fov_tans(lens: float = 85.0, sensor: float = 36.0) -> tuple[float, float]:
    scene = bpy.context.scene
    aspect = scene.render.resolution_y / scene.render.resolution_x
    tan_h = sensor / (2 * lens)
    return tan_h, tan_h * aspect


def aim_camera(target: Vector, azimuth: float, elevation: float, distance: float) -> None:
    camera_data = bpy.data.cameras.new("Camera")
    camera_data.lens = 85  # Long enough to avoid wide-angle distortion.
    camera = bpy.data.objects.new("Camera", camera_data)
    camera.location = target + _spherical(azimuth, elevation) * distance
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    track_to(camera, target)


def track_to(obj, target: Vector) -> None:
    empty = bpy.data.objects.new(f"{obj.name}_target", None)
    empty.location = target
    bpy.context.collection.objects.link(empty)
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = empty
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def arrange_in_row(objects, gap: float) -> None:
    """Lay parts out side by side, spaced by their own widths.

    Hand-picked coordinates do not survive a design change: the pod grew when
    the corner posts were added and promptly overlapped its neighbour.
    """
    widths = [_size(obj).x for obj in objects]
    total = sum(widths) + gap * (len(objects) - 1)

    cursor = -total / 2
    for obj, width in zip(objects, widths):
        obj.location = (cursor + width / 2 - _centre(obj).x, -_centre(obj).y, 0.0)
        bpy.context.view_layer.update()
        obj.location.z = -min(corner.z for corner in world_corners(obj))
        bpy.context.view_layer.update()
        cursor += width + gap


def _size(obj) -> Vector:
    corners = world_corners(obj)
    return Vector([max(c[i] for c in corners) - min(c[i] for c in corners) for i in range(3)])


def _centre(obj) -> Vector:
    corners = world_corners(obj)
    return Vector([(max(c[i] for c in corners) + min(c[i] for c in corners)) / 2 for i in range(3)])


def world_corners(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def bounds_centre(objects) -> Vector:
    corners = [c for obj in objects for c in world_corners(obj)]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    return (lo + hi) / 2


# --- Render -----------------------------------------------------------------


def configure_render(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.fps = 30
    scene.render.film_transparent = False
    if _has_agx():
        scene.view_settings.look = "AgX - Medium High Contrast"
    use_gpu()


def _has_agx() -> bool:
    try:
        return "AgX - Medium High Contrast" in {
            item.identifier
            for item in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items
        }
    except Exception:
        return False


def use_gpu() -> None:
    """Prefer Metal on Apple silicon, fall back to CPU without complaint."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("METAL", "OPTIX", "CUDA", "HIP"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            if any(device.type == backend for device in prefs.devices):
                for device in prefs.devices:
                    device.use = device.type in (backend, "CPU")
                bpy.context.scene.cycles.device = "GPU"
                return
    except Exception as error:  # pragma: no cover - depends on the machine
        print(f"cycles: GPU setup skipped ({error})")
    bpy.context.scene.cycles.device = "CPU"


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def render_still(path: Path) -> None:
    scene = bpy.context.scene
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "IMAGE"
    settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_animation(path: Path) -> None:
    scene = bpy.context.scene
    settings = scene.render.image_settings
    # Blender 5 split image and video output behind media_type; FFMPEG is not
    # in the file_format enum at all until the media type says VIDEO.
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.filepath = str(path.with_suffix(""))
    bpy.ops.render.render(animation=True)

    # Blender names video output after the frame range, so the file lands as
    # `turntable0001-0096.mp4`. Rename it to something a slide can reference.
    produced = sorted(path.parent.glob(f"{path.stem}[0-9]*{path.suffix}"))
    if produced:
        produced[-1].replace(path)


if __name__ == "__main__":
    main()
