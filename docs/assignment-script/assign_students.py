"""
Prof. Fletcher's project assignment script (min-cost flow).

The algorithm is unchanged from the original. The only change is that student
preferences are now read from a CSV file (exported from UniFlow) instead of
being typed into the script.

Run:  python assign_students.py preferences.csv
See README.md in this folder for the file format.
"""
import csv
import sys

import networkx as nx

G = nx.DiGraph()

# ---------------------------------------------------------------------------
# INPUT 1 of 2: student preferences, read from the CSV given on the command line
# CSV columns: student, choice_1, choice_2, choice_3
# ---------------------------------------------------------------------------
csv_path = sys.argv[1] if len(sys.argv) > 1 else 'sample_preferences.csv'
prefs = {}
with open(csv_path, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        choices = [row['choice_1'], row['choice_2'], row['choice_3']]
        prefs[row['student']] = [c.strip() for c in choices if c and c.strip()]

# ---------------------------------------------------------------------------
# INPUT 2 of 2: project capacities (edit these for each run)
# project name -> maximum number of students (0 = project closed)
# ---------------------------------------------------------------------------
capacities = {
    'Project1': 3,
    'Project2': 3,
    'Project3': 4,
    'Project4': 3,
    'Project5': 0,
}

# ---------------------------------------------------------------------------
# Algorithm (unchanged from the original script)
# ---------------------------------------------------------------------------
num_persons = len(prefs)
G.add_node('dest', demand=num_persons)
A = []
for person, projectlist in prefs.items():
    G.add_node(person, demand=-1)
    for i, project in enumerate(projectlist):
        if i == 0:
            cost = -100  # happy to assign first choice
        elif i == 1:
            cost = -66   # slightly unhappy to assign second choice
        # elif i == 2:
        #     cost = -50  # ok to assign third choice
        else:
            cost = -33   # very unhappy to assign fourth choice
        G.add_edge(person, project, capacity=1, weight=cost)  # Edge taken if person does this project

for project, c in capacities.items():
    G.add_edge(project, 'dest', capacity=c, weight=0)

flowdict = nx.min_cost_flow(G)
for person in prefs:
    for project, flow in flowdict[person].items():
        if flow:
            print(person, 'joins', project)
