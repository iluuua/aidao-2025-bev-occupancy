# Task specification and reference material

The organizers handed out a task deck and two lectures on the educational day that opened the
final. This page records what the task actually specified and which architectures were pointed at,
so the solution can be read against its original brief.

The source decks are the property of Yandex Education and the HSE Faculty of Computer Science and
are not redistributed here. What follows is a factual summary with attribution, plus links to the
public papers the decks cite.

## The task as specified

Source: *AIDAO — static grids*, Yandex Education × HSE Faculty of Computer Science, final round,
29–30 November 2025.

**Goal.** Recognise static obstacles around the car and express them as an occupancy grid in
bird's-eye view. The deck illustrates the target class with concrete road furniture, concrete
barriers and guardrails, rather than with an abstract definition.

**Ground truth.** Grids of shape `(188, 126)`, with `0 = free` and `1 = occupied`, plus an ignore
label for unknown cells.

**Data split.**

| Split | Scenes | Notes |
|---|---|---|
| train | 4000 | with `static_grids/` ground truth |
| val | 1000 | with `static_grids/` ground truth |
| test | 2000 | public and private division known only to the organizers |

**Directory layout.** Train and val ship `info.csv`, `images/`, `matrices/` and `static_grids/`.
Test ships `info.csv`, `images/`, `matrices/` and `predicted_static_grids/`, part of which is
submitted.

**Metric.** The deck states the standard formula, `IoU = TP / (TP + FP + FN)`.

Note on the metric: this repository's notebook additionally reports a **mean** IoU averaged over
the free and occupied classes, and the training loss uses a differentiable surrogate of that mean.
Averaging both classes was a choice made during the contest, not part of the stated metric. The
0.5606 figure quoted in the main README is the leaderboard score under the organizers' own metric.

**Required submission.** `info.csv`, `predicted_static_grids/`, `model.pt`, all code needed to
reproduce the best submission, a `README.md` with instructions for inference and training, and
either a `requirements.txt` with pinned versions or a Dockerfile.

**Constraints.** The deck states that using methods or materials carrying an incorrect licence
leads to disqualification, and reminds participants that an olympiad with a prize fund is a
commercial event.

## Architectures the organizers pointed at

The task deck presents **BEVFusion** as the framing example, first as a detector and then with its
BEV map segmentation head highlighted, which is the head closest to this task. The lecture
*Detector architectures* by Sergey Kim, from the pretraining group of Yandex's autonomous transport
unit, covers 2D detection and then 3D detection split into BEV-based and BEV-free approaches.

| Paper | Where it came up |
|---|---|
| [BEVFusion](https://arxiv.org/abs/2205.13542) | task deck, framing example and segmentation head |
| [Lift-Splat-Shoot](https://arxiv.org/abs/2008.05711) | the architecture this solution implements |
| [R-CNN](https://arxiv.org/abs/1311.2524) | detector lecture, 2D detection |
| [FCOS](https://arxiv.org/abs/1904.01355) | detector lecture, 2D detection |
| [DETR](https://arxiv.org/abs/2005.12872) | detector lecture, 2D detection |

## What this changes about the solution

Reading the brief back against the code confirms the numbers in the notebook: 4000 training scenes,
1000 validation, 2000 test, grids of `(188, 126)`, and the `info.csv` plus `matrices/` layout the
dataset class expects. It also shows the intended framing was BEV segmentation as one head of a
detector-style stack, which is what Lift-Splat-Shoot provides in isolation.

A third lecture from the same day, on cascaded text-to-texture synthesis for 3D models, is
unrelated to this task and is not summarised here.
