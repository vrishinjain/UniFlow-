# Project assignment script

Prof. Fletcher's script for assigning students to projects based on their ranked preferences. It solves the assignment as a **min-cost flow** problem (using `networkx`), so it finds the assignment that gives the most students their highest choices while respecting each project's capacity.

**How it fits into UniFlow:** faculty clicks **Export preferences** on a course, which downloads a CSV in the format below. That CSV is passed to this script, which prints each student's assigned project.

| File | What it is |
|---|---|
| `assign_students.py` | The script. The algorithm is unchanged from the original; the only change is that student preferences are read from a CSV instead of being typed into the script. |
| `sample_preferences.csv` | Sample input, in the same format UniFlow's export produces. Made-up students, because this repo is public. |
| `sample_output.txt` | The exact output of running the script on `sample_preferences.csv`. |

## How to run

**Requirements:** Python 3 (tested with 3.13) and `networkx` (tested with 3.7).

```bash
pip install networkx
python assign_students.py sample_preferences.csv
```

Replace `sample_preferences.csv` with the file exported from UniFlow. The result is printed to the terminal; to save it to a file:

```bash
python assign_students.py preferences.csv > output.txt
```

## Input 1: preferences CSV (exported from UniFlow)

One row per student, with a header row:

```csv
student,choice_1,choice_2,choice_3
alex.rivera@example.edu,Project1,Project2,Project3
bianca.chen@example.edu,Project1,Project3,Project4
```

| Column | Meaning | From UniFlow |
|---|---|---|
| `student` | Unique identifier for the student. Use the email: it's unique, and the professor can read it. | `users` email of `student_preference.student` |
| `choice_1` | The student's 1st choice project | `student_preference.project` where `rank = 1` |
| `choice_2` | 2nd choice | `rank = 2` |
| `choice_3` | 3rd choice | `rank = 3` |

Rules for the export:
- Columns must be named exactly as above, in UTF-8, with a header row.
- Only students in the selected course.
- Project values must match the project names in `capacities` (Input 2) exactly, so project names must be unique within a course.
- If a student ranked fewer than 3 projects, leave the missing choice cells empty.

## Input 2: project capacities (in the script)

Capacities are still set inside the script, as in the original:

```python
capacities = {
    'Project1': 3,
    ...
    'Project5': 0,
}
```

| Part | Meaning |
|---|---|
| Key | The project name (must match the names used in the CSV) |
| Value | Maximum number of students the project can take. `0` means the project is closed and nobody will be assigned to it. |

## Output format

One line per student, in the same order as the CSV:

```
<student> joins <project>
```

For example, from `sample_output.txt`:

```
alex.rivera@example.edu joins Project2
bianca.chen@example.edu joins Project3
carlos.diaz@example.edu joins Project1
```

Every student appears exactly once. Because `student` is an email, each line can be matched back to a UniFlow user to create a `project_assignment` row.

## How the assignment is chosen

Each choice has a score, and the script picks the assignment with the best total score across the whole class:

| Choice | Weight in the script |
|---|---|
| 1st | -100 |
| 2nd | -66 |
| 3rd | -33 |

(The weights are negative because the algorithm minimises cost.) Students are only ever placed in a project they ranked. Running the script twice on the same input gives the same result.

In the sample, Project1 is ranked first by five students but only has 3 places, and Project5 is closed. So 8 of the 12 students get their 1st choice and the other 4 get their 2nd choice.

## Rules and limits

- **Every student must be placeable.** There is no "unassigned" result. If the open projects a student ranked don't have enough room, the script stops with `networkx.exception.NetworkXUnfeasible: no flow satisfies all node demands` instead of printing anything. Fix it by raising capacities or getting more choices from students.
- **Total capacity** of open projects must be at least the number of students.
- **A project that's in the CSV but not in `capacities`** can't receive anyone; students who ranked it get their next choice.
- **Duplicate students:** if the same `student` appears twice in the CSV, only the last row is used.
