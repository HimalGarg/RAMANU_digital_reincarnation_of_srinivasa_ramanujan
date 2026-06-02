"""
scripts/render_visual.py — Safe Fractal Engine Renderer
======================================================
Parses structured JSON visualization parameters and renders
parameterized mathematical animations using Manim.
"""

import argparse
import json
import os
import shutil
import sys
import numpy as np

# Configure Manim settings before importing Manim elements
from manim import config
config.background_color = "#0B0C10"  # Sleek modern dark background
config.pixel_width = 854
config.pixel_height = 480
config.frame_rate = 30
config.quality = "low_quality"
config.verbosity = "WARNING"
config.media_dir = "data/visualizations"

from manim import *

# ─── 1. Continued Fraction Scene ──────────────────────────────────────────────

class ContinuedFractionMobject(VGroup):
    """Recursively constructed Continued Fraction layout without LaTeX compile dependencies."""
    def __init__(self, terms, depth=0, max_depth=5, **kwargs):
        super().__init__(**kwargs)
        if depth >= len(terms) or depth >= max_depth:
            dot_dot_dot = Text("...", font="Consolas", color=GRAY, font_size=20)
            self.add(dot_dot_dot)
            return

        a_val = str(terms[depth])
        a_text = Text(a_val, font="Segoe UI", color=YELLOW_C, font_size=24)
        
        if depth == len(terms) - 1:
            self.add(a_text)
            return
            
        plus_text = Text(" + ", font="Segoe UI", color=WHITE, font_size=20)
        num_text = Text("1", font="Segoe UI", color=TEAL, font_size=20)
        
        # Recursive denominator
        denom_mobject = ContinuedFractionMobject(terms, depth + 1, max_depth)
        
        # Scale down nested fractions
        scale_factor = 0.85
        denom_mobject.scale(scale_factor)
        
        # Layout fraction vertically
        num_w = num_text.width
        denom_w = denom_mobject.width
        line_w = max(num_w, denom_w) + 0.3
        
        div_line = Line(
            start=LEFT * (line_w / 2),
            end=RIGHT * (line_w / 2),
            color=WHITE,
            stroke_width=1.5
        )
        
        fraction_group = VGroup(num_text, div_line, denom_mobject)
        fraction_group.arrange(DOWN, buff=0.12)
        
        # Layout integer part + plus sign to the left of the fraction line
        left_group = VGroup(a_text, plus_text).arrange(RIGHT, buff=0.08)
        left_group.next_to(div_line, LEFT, buff=0.15)
        
        self.add(left_group, fraction_group)


class ContinuedFractionScene(Scene):
    def __init__(self, terms, title="Ramanujan Continued Fraction", **kwargs):
        self.terms = terms
        self.title_text = title
        super().__init__(**kwargs)

    def compute_convergents(self):
        convergents = []
        for i in range(1, len(self.terms) + 1):
            try:
                # compute the value of self.terms[:i]
                val = float(self.terms[i-1])
                for term in reversed(self.terms[:i-1]):
                    if val == 0:
                        val = 1e-9
                    val = float(term) + 1.0 / val
                convergents.append(round(val, 5))
            except Exception:
                convergents.append(None)
        return convergents

    def construct(self):
        title = Text(self.title_text, font="Segoe UI", color=GOLD, font_size=32)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title))
        self.wait(0.3)

        convergents = self.compute_convergents()
        
        # Display the convergent label at the bottom
        convergent_label = Text("Convergent: ", font="Segoe UI", color=BLUE_C, font_size=20)
        convergent_label.to_edge(DOWN, buff=0.5).shift(LEFT * 1.5)
        
        convergent_val_text = Text("", font="Segoe UI", color=YELLOW, font_size=20)
        convergent_val_text.next_to(convergent_label, RIGHT, buff=0.2)
        
        self.play(FadeIn(convergent_label))

        current_cf = None

        for depth in range(len(self.terms)):
            # Build continued fraction for this depth
            new_cf = ContinuedFractionMobject(self.terms, max_depth=depth + 1)
            new_cf.move_to(ORIGIN + DOWN * 0.2)
            
            # Formulate the convergent text
            conv_val = convergents[depth]
            if conv_val is not None:
                new_val_text = Text(f"c_{depth} = {conv_val}", font="Segoe UI", color=YELLOW, font_size=20)
            else:
                new_val_text = Text(f"c_{depth} = ?", font="Segoe UI", color=YELLOW, font_size=20)
            new_val_text.next_to(convergent_label, RIGHT, buff=0.2)

            if depth == 0:
                current_cf = new_cf
                self.play(FadeIn(current_cf, shift=UP * 0.2), FadeIn(convergent_val_text))
                self.play(ReplacementTransform(convergent_val_text, new_val_text))
            else:
                self.play(
                    ReplacementTransform(current_cf, new_cf),
                    ReplacementTransform(convergent_val_text, new_val_text),
                    run_time=1.2
                )
                current_cf = new_cf
            
            convergent_val_text = new_val_text
            self.wait(1.0)
            
        self.wait(1.5)

# ─── 2. Partition Grid Scene ──────────────────────────────────────────────────

class PartitionGridScene(Scene):
    def __init__(self, n, partitions=None, **kwargs):
        self.n = int(n)
        if partitions is None:
            self.partitions = self.get_partitions(self.n)
        else:
            self.partitions = partitions
        super().__init__(**kwargs)

    def get_partitions(self, n):
        def helper(n, max_val):
            if n == 0:
                return [[]]
            res = []
            for i in range(min(n, max_val), 0, -1):
                for p in helper(n - i, i):
                    res.append([i] + p)
            return res
        # Limit partitions list to avoid excessively long renders (max 8 partitions)
        all_parts = helper(n, n)
        return all_parts[:8]

    def construct(self):
        title = Text(f"Partitions of n = {self.n}", font="Segoe UI", color=GOLD, font_size=32)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title))
        
        count_text = Text(f"Displaying partition representations", font="Segoe UI", color=BLUE_C, font_size=20)
        count_text.next_to(title, DOWN, buff=0.15)
        self.play(FadeIn(count_text))
        self.wait(0.3)

        current_partition_mobs = VGroup()
        partition_label = VMobject()

        for idx, p in enumerate(self.partitions):
            new_mobs = VGroup()
            square_size = 0.4
            
            # Create a block representation for each row in the partition
            for row_idx, row_len in enumerate(p):
                for col_idx in range(row_len):
                    sq = Square(
                        side_length=square_size,
                        fill_color=TEAL,
                        fill_opacity=0.6,
                        stroke_color=WHITE,
                        stroke_width=1.2
                    )
                    sq.move_to(RIGHT * col_idx * square_size + DOWN * row_idx * square_size)
                    new_mobs.add(sq)
            
            new_mobs.move_to(ORIGIN + DOWN * 0.4)
            
            parts_str = " + ".join(map(str, p))
            label_text = Text(f"{self.n} = {parts_str}", font="Segoe UI", color=YELLOW, font_size=26)
            label_text.next_to(new_mobs, UP, buff=0.3)
            
            if idx == 0:
                current_partition_mobs = new_mobs
                partition_label = label_text
                self.play(FadeIn(current_partition_mobs), FadeIn(partition_label))
            else:
                # Smooth morphing transition between partition diagrams
                self.play(
                    ReplacementTransform(current_partition_mobs, new_mobs),
                    ReplacementTransform(partition_label, label_text),
                    run_time=1.0
                )
                current_partition_mobs = new_mobs
                partition_label = label_text
                
            self.wait(0.8)
            
        self.wait(1.5)

class GridCube(VGroup):
    """3D Cube constructed from 6 grid faces to represent voxels in a detailed Rubik-style look."""
    def __init__(self, n_side, fill_color, scale, **kwargs):
        super().__init__(**kwargs)
        self.n_side = int(n_side)
        side_len = self.n_side * scale
        d = side_len / self.n_side
        
        # Create one face grid (aligned on XY plane at z=0)
        def make_face():
            face = VGroup()
            for i in range(self.n_side):
                for j in range(self.n_side):
                    sq = Square(
                        side_length=d,
                        fill_color=fill_color,
                        fill_opacity=0.4,
                        stroke_color=WHITE,
                        stroke_width=0.8
                    )
                    sq.move_to(np.array([
                        -side_len/2 + d/2 + i*d,
                        -side_len/2 + d/2 + j*d,
                        0
                    ]))
                    face.add(sq)
            return face

        # Front
        f_front = make_face().shift(OUT * (side_len / 2))
        # Back
        f_back = make_face().shift(IN * (side_len / 2))
        # Right
        f_right = make_face().rotate(90 * DEGREES, axis=UP).shift(RIGHT * (side_len / 2))
        # Left
        f_left = make_face().rotate(-90 * DEGREES, axis=UP).shift(LEFT * (side_len / 2))
        # Top
        f_top = make_face().rotate(90 * DEGREES, axis=RIGHT).shift(UP * (side_len / 2))
        # Bottom
        f_bottom = make_face().rotate(-90 * DEGREES, axis=RIGHT).shift(DOWN * (side_len / 2))
        
        self.add(f_front, f_back, f_right, f_left, f_top, f_bottom)


# ─── 3. Taxicab 3D Scene ──────────────────────────────────────────────────────

class Taxicab3DScene(ThreeDScene):
    def __init__(self, n=1729, pairs=None, **kwargs):
        self.n = int(n)
        self.pairs = pairs or [[9, 10], [1, 12]]
        super().__init__(**kwargs)

    def construct(self):
        # Position camera in 3D space
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        
        # 2D overlays (titles)
        title = Text(f"Taxicab Number: {self.n}", font="Segoe UI", color=GOLD, font_size=32)
        self.add_fixed_in_frame_mobjects(title)
        title.to_edge(UP, buff=0.4)
        
        scale = 0.22
        
        # First representation
        pair1 = self.pairs[0]
        a1, b1 = int(pair1[0]), int(pair1[1])
        
        cube_a1 = GridCube(n_side=a1, fill_color=TEAL, scale=scale)
        cube_a1.move_to(LEFT * 1.8)
        
        label_a1 = Text(f"{a1}^3 = {a1**3}", font="Segoe UI", color=YELLOW, font_size=18)
        self.add_fixed_in_frame_mobjects(label_a1)
        label_a1.move_to(LEFT * 1.8 + DOWN * 1.8)
        
        cube_b1 = GridCube(n_side=b1, fill_color=BLUE, scale=scale)
        cube_b1.move_to(RIGHT * 1.2)
        
        label_b1 = Text(f"{b1}^3 = {b1**3}", font="Segoe UI", color=YELLOW, font_size=18)
        self.add_fixed_in_frame_mobjects(label_b1)
        label_b1.move_to(RIGHT * 1.2 + DOWN * 1.8)
        
        equation1 = Text(f"{a1}^3 + {b1}^3 = {a1**3} + {b1**3} = {self.n}", font="Segoe UI", color=WHITE, font_size=22)
        self.add_fixed_in_frame_mobjects(equation1)
        equation1.move_to(DOWN * 2.6)

        self.play(FadeIn(cube_a1), FadeIn(label_a1))
        self.play(FadeIn(cube_b1), FadeIn(label_b1))
        self.play(Write(equation1))
        
        self.begin_ambient_camera_rotation(rate=0.12)
        self.wait(2.5)
        self.stop_ambient_camera_rotation()
        
        # Second representation
        pair2 = self.pairs[1]
        a2, b2 = int(pair2[0]), int(pair2[1])
        
        cube_a2 = GridCube(n_side=a2, fill_color=TEAL, scale=scale)
        cube_a2.move_to(LEFT * 1.8)
        
        label_a2 = Text(f"{a2}^3 = {a2**3}", font="Segoe UI", color=YELLOW, font_size=18)
        self.add_fixed_in_frame_mobjects(label_a2)
        label_a2.move_to(LEFT * 1.8 + DOWN * 1.8)
        
        cube_b2 = GridCube(n_side=b2, fill_color=BLUE, scale=scale)
        cube_b2.move_to(RIGHT * 1.2)
        
        label_b2 = Text(f"{b2}^3 = {b2**3}", font="Segoe UI", color=YELLOW, font_size=18)
        self.add_fixed_in_frame_mobjects(label_b2)
        label_b2.move_to(RIGHT * 1.2 + DOWN * 1.8)
        
        equation2 = Text(f"{a2}^3 + {b2}^3 = {a2**3} + {b2**3} = {self.n}", font="Segoe UI", color=WHITE, font_size=22)
        self.add_fixed_in_frame_mobjects(equation2)
        equation2.move_to(DOWN * 2.6)
        
        # Perform smooth morphing transition
        self.play(
            ReplacementTransform(cube_a1, cube_a2),
            ReplacementTransform(cube_b1, cube_b2),
            ReplacementTransform(label_a1, label_a2),
            ReplacementTransform(label_b1, label_b2),
            ReplacementTransform(equation1, equation2),
            run_time=1.8
        )
        
        self.begin_ambient_camera_rotation(rate=-0.12)
        self.wait(2.5)
        self.stop_ambient_camera_rotation()
        self.wait(1.0)

# ─── Main Orchestrator ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Render parameterized Manim animations from JSON configurations.")
    parser.add_argument("--json", required=True, help="JSON visualization configuration string or path to a JSON file.")
    parser.add_argument("--output", default="data/visualizations/output.mp4", help="Copy final video output to this path.")
    args = parser.parse_args()

    # Parse JSON
    try:
        if os.path.exists(args.json):
            with open(args.json, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(args.json)
    except Exception as e:
        print(f"Error parsing JSON configuration: {e}", file=sys.stderr)
        sys.exit(1)

    vis_type = data.get("visualization_type")
    params = data.get("parameters", {})

    print(f"[*] Rendering visualization: '{vis_type}'...")

    scene_instance = None
    scene_name = ""

    if vis_type == "continued_fraction":
        terms = params.get("terms", [1, 1, 1, 1])
        title = params.get("title", "Ramanujan Continued Fraction")
        scene_instance = ContinuedFractionScene(terms=terms, title=title)
        scene_name = "ContinuedFractionScene"

    elif vis_type == "partition_grid":
        n = params.get("n", 5)
        partitions = params.get("partitions", None)
        scene_instance = PartitionGridScene(n=n, partitions=partitions)
        scene_name = "PartitionGridScene"

    elif vis_type == "taxicab":
        n = params.get("n", 1729)
        pairs = params.get("pairs", [[9, 10], [1, 12]])
        scene_instance = Taxicab3DScene(n=n, pairs=pairs)
        scene_name = "Taxicab3DScene"

    else:
        print(f"Error: Unknown visualization type '{vis_type}'", file=sys.stderr)
        sys.exit(1)

    # Render scene
    try:
        scene_instance.render()
    except Exception as e:
        print(f"Error during Manim compilation: {e}", file=sys.stderr)
        sys.exit(1)

    # Find compiled file and copy to desired output
    compiled_path = None
    for root, dirs, files in os.walk(config.media_dir):
        for file in files:
            if file == f"{scene_name}.mp4":
                compiled_path = os.path.join(root, file)
                break
        if compiled_path:
            break

    if compiled_path and os.path.exists(compiled_path):
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        shutil.copy2(compiled_path, args.output)
        print(f"[OK] Render completed! Output saved to: {args.output}")
    else:
        print(f"Error: Could not locate rendered video for scene '{scene_name}' under: {config.media_dir}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
