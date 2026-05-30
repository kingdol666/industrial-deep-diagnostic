#!/usr/bin/env python3
"""
Tests for the Ontology Builder module.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_ontology import OntologyBuilder


def test_ontology_builder_initialization():
    builder = OntologyBuilder(domain="pva_bopet")
    graph = builder.graph
    assert len(graph) > 0
    class_nodes = [n for n in graph if n.get("@type") == "owl:Class"]
    assert len(class_nodes) > 5, f"Expected >5 class nodes, got {len(class_nodes)}"
    print("  Ontology builder initialization: PASS")


def test_add_material_instance():
    builder = OntologyBuilder(domain="pva_bopet")
    mat_id = builder.add_material_instance("PVA 1799", "Polymer")
    assert "Polymer_PVA_1799" in mat_id
    add_id = builder.add_additive_instance("CNC")
    assert "Additive_CNC" in add_id
    print("  Add material instances: PASS")


def test_build_from_experiments():
    builder = OntologyBuilder(domain="pva_bopet")

    experiments = [
        {
            "experiment_id": "SRC_0001_E01",
            "material_system": "PVA 1799",
            "additive": "CNC",
            "additive_concentration": 3,
            "paper_title": "Enhanced PVA CNC composites",
            "year": 2020,
            "doi": "10.1234/test.001",
        },
        {
            "experiment_id": "SRC_0001_E02",
            "material_system": "PVA 1799",
            "additive": "GO",
            "additive_concentration": 1,
            "paper_title": "PVA GO films",
            "year": 2021,
            "doi": "10.1234/test.002",
        },
        {
            "experiment_id": "SRC_0002_E01",
            "material_system": "PET",
            "additive": "SiO2",
            "paper_title": "PET silica coatings",
            "year": 2019,
            "doi": "10.1234/test.003",
        },
    ]

    ontology = builder.build_from_experiments(experiments)

    graph = ontology.get("@graph", [])
    polymer_nodes = [n for n in graph if "Polymer" in str(n.get("@type", ""))]
    additive_nodes = [n for n in graph if "Additive" in str(n.get("@type", ""))]
    source_nodes = [n for n in graph if "Source" in str(n.get("@type", ""))]

    assert len(polymer_nodes) >= 2, f"Expected at least 2 polymer nodes, got {len(polymer_nodes)}"
    assert len(additive_nodes) >= 3, f"Expected at least 3 additive nodes, got {len(additive_nodes)}"
    assert len(source_nodes) >= 3, f"Expected at least 3 source nodes, got {len(source_nodes)}"

    context = ontology.get("@context", {})
    assert "rdf" in context
    assert "pva" in context or "rdfs" in context

    print("  Build from experiments: PASS")


def test_turtle_output():
    builder = OntologyBuilder(domain="pva_bopet")
    builder.add_material_instance("PVA 1799", "Polymer")
    builder.add_additive_instance("CNC")

    ontology = {"@graph": builder.graph}
    turtle = builder.to_turtle(ontology)

    assert "@prefix" in turtle
    assert "PVA 1799" in turtle
    assert "owl:Class" in turtle or "a " in turtle

    print("  Turtle output: PASS")


if __name__ == "__main__":
    print("Testing Ontology Builder:")
    test_ontology_builder_initialization()
    test_add_material_instance()
    test_build_from_experiments()
    test_turtle_output()
    print("All Ontology Builder tests passed!")