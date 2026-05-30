#!/usr/bin/env python3
"""
Ontology Builder: constructs an OWL/JSON-LD ontology from normalized experiment data.
Supports output in JSON-LD, RDF/Turtle, and graph schema formats.
"""

import json
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).resolve().parent.parent

ONTOLOGY_BASE = "http://example.org/ontology/pva-bopet/"

BASE_CLASSES = [
    {
        "@id": f"{ONTOLOGY_BASE}Material",
        "@type": "owl:Class",
        "rdfs:label": "Material",
        "rdfs:comment": "Any substance used in film formation: polymer matrix, additive, or solvent"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Polymer",
        "@type": "owl:Class",
        "rdfs:subClassOf": {"@id": f"{ONTOLOGY_BASE}Material"},
        "rdfs:label": "Polymer"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Additive",
        "@type": "owl:Class",
        "rdfs:subClassOf": {"@id": f"{ONTOLOGY_BASE}Material"},
        "rdfs:label": "Additive"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Solvent",
        "@type": "owl:Class",
        "rdfs:subClassOf": {"@id": f"{ONTOLOGY_BASE}Material"},
        "rdfs:label": "Solvent"
    },
    {
        "@id": f"{ONTOLOGY_BASE}ProcessStep",
        "@type": "owl:Class",
        "rdfs:label": "ProcessStep",
        "rdfs:comment": "A step in the film fabrication process"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Instrument",
        "@type": "owl:Class",
        "rdfs:label": "Instrument",
        "rdfs:comment": "Measurement or processing instrument"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Condition",
        "@type": "owl:Class",
        "rdfs:label": "Condition",
        "rdfs:comment": "An experimental condition (temperature, time, pressure, etc.)"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Measurement",
        "@type": "owl:Class",
        "rdfs:label": "Measurement",
        "rdfs:comment": "A measured property value"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Property",
        "@type": "owl:Class",
        "rdfs:label": "Property",
        "rdfs:comment": "A measurable property type"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Result",
        "@type": "owl:Class",
        "rdfs:label": "Result",
        "rdfs:comment": "An experimental result or observation"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Source",
        "@type": "owl:Class",
        "rdfs:label": "Source",
        "rdfs:comment": "A literature source (paper, patent, report)"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Evidence",
        "@type": "owl:Class",
        "rdfs:label": "Evidence",
        "rdfs:comment": "Evidence linking a measurement to its source"
    },
    {
        "@id": f"{ONTOLOGY_BASE}Experiment",
        "@type": "owl:Class",
        "rdfs:label": "Experiment",
        "rdfs:comment": "A complete experiment conducted in a paper"
    },
]

BASE_OBJECT_PROPERTIES = [
    {
        "@id": f"{ONTOLOGY_BASE}hasAdditive",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Polymer"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Additive"},
        "rdfs:label": "has additive"
    },
    {
        "@id": f"{ONTOLOGY_BASE}usesMethod",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Experiment"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}ProcessStep"},
        "rdfs:label": "uses preparation method"
    },
    {
        "@id": f"{ONTOLOGY_BASE}usesInstrument",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Measurement"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Instrument"},
        "rdfs:label": "uses instrument"
    },
    {
        "@id": f"{ONTOLOGY_BASE}underCondition",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Experiment"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Condition"},
        "rdfs:label": "under condition"
    },
    {
        "@id": f"{ONTOLOGY_BASE}hasProperty",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Material"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Property"},
        "rdfs:label": "has property"
    },
    {
        "@id": f"{ONTOLOGY_BASE}producesResult",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Experiment"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Result"},
        "rdfs:label": "produces result"
    },
    {
        "@id": f"{ONTOLOGY_BASE}reportedIn",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Result"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Source"},
        "rdfs:label": "reported in"
    },
    {
        "@id": f"{ONTOLOGY_BASE}hasEvidence",
        "@type": "owl:ObjectProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Measurement"},
        "rdfs:range": {"@id": f"{ONTOLOGY_BASE}Evidence"},
        "rdfs:label": "has evidence"
    },
]

BASE_DATA_PROPERTIES = [
    {
        "@id": f"{ONTOLOGY_BASE}hasValue",
        "@type": "owl:DatatypeProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Property"},
        "rdfs:range": {"@id": "xsd:double"},
        "rdfs:label": "has value"
    },
    {
        "@id": f"{ONTOLOGY_BASE}hasUnit",
        "@type": "owl:DatatypeProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Property"},
        "rdfs:range": {"@id": "xsd:string"},
        "rdfs:label": "has unit"
    },
    {
        "@id": f"{ONTOLOGY_BASE}hasConfidence",
        "@type": "owl:DatatypeProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Evidence"},
        "rdfs:range": {"@id": "xsd:double"},
        "rdfs:label": "has confidence score"
    },
    {
        "@id": f"{ONTOLOGY_BASE}doi",
        "@type": "owl:DatatypeProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Source"},
        "rdfs:range": {"@id": "xsd:string"},
        "rdfs:label": "DOI"
    },
    {
        "@id": f"{ONTOLOGY_BASE}year",
        "@type": "owl:DatatypeProperty",
        "rdfs:domain": {"@id": f"{ONTOLOGY_BASE}Source"},
        "rdfs:range": {"@id": "xsd:integer"},
        "rdfs:label": "publication year"
    },
]


class OntologyBuilder:
    def __init__(self, domain: str = "pva_bopet"):
        self.domain = domain
        self.base = f"http://example.org/ontology/{domain}/"
        self.graph = []
        self.graph.extend(BASE_CLASSES)
        self.graph.extend(BASE_OBJECT_PROPERTIES)
        self.graph.extend(BASE_DATA_PROPERTIES)
        self._seen_individuals = set()

    def _sanitize_id(self, name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', name.replace(' ', '_'))

    def add_material_instance(self, name: str, mat_type: str = "Polymer"):
        safe_id = self._sanitize_id(name)
        individual_id = f"{self.base}{mat_type}_{safe_id}"
        if individual_id in self._seen_individuals:
            return individual_id
        self._seen_individuals.add(individual_id)
        self.graph.append({
            "@id": individual_id,
            "@type": f"{self.base}{mat_type}",
            "rdfs:label": name
        })
        return individual_id

    def add_additive_instance(self, name: str):
        return self.add_material_instance(name, "Additive")

    def add_source_instance(self, paper: dict):
        source_id = paper.get("source_id") or paper.get("doi") or "UNKNOWN"
        safe_id = self._sanitize_id(str(source_id))
        if not safe_id:
            safe_id = self._sanitize_id(paper.get("title", paper.get("doi", "UNKNOWN")))
        individual_id = f"{self.base}Source_{safe_id}"
        if individual_id in self._seen_individuals:
            return individual_id
        self._seen_individuals.add(individual_id)
        node = {
            "@id": individual_id,
            "@type": f"{self.base}Source",
            "rdfs:label": paper.get("title", source_id)
        }
        doi = paper.get("doi")
        if doi:
            node[f"{self.base}doi"] = str(doi)
        year = paper.get("year")
        if year:
            node[f"{self.base}year"] = int(year)
        self.graph.append(node)
        return individual_id

    def add_property_instance(self, prop_name: str, value: float, unit: str):
        safe_id = self._sanitize_id(prop_name)
        individual_id = f"{self.base}Property_{safe_id}_{len(self._seen_individuals)}"
        self._seen_individuals.add(individual_id)
        self.graph.append({
            "@id": individual_id,
            "@type": f"{self.base}Property",
            "rdfs:label": prop_name,
            f"{self.base}hasValue": value,
            f"{self.base}hasUnit": unit
        })
        return individual_id

    def add_relationship(self, subject_id: str, predicate: str, object_id: str):
        if subject_id in self._seen_individuals and object_id in self._seen_individuals:
            for node in self.graph:
                if node.get("@id") == subject_id:
                    pred_key = f"{self.base}{predicate}"
                    existing = node.get(pred_key)
                    if existing is None:
                        node[pred_key] = {"@id": object_id}
                    elif isinstance(existing, dict):
                        node[pred_key] = [existing, {"@id": object_id}]
                    elif isinstance(existing, list):
                        existing.append({"@id": object_id})
                    break

    def build_from_experiments(self, experiments: list) -> dict:
        for exp in experiments:
            mat_name = exp.get("material_system", "")
            if mat_name:
                mat_id = self.add_material_instance(mat_name, "Polymer")

            add_name = exp.get("additive", "")
            if add_name and mat_name:
                add_id = self.add_additive_instance(add_name)
                self.add_relationship(mat_id, "hasAdditive", add_id)

            source_info = {
                "source_id": exp.get("source_id", ""),
                "title": exp.get("paper_title", ""),
                "doi": exp.get("doi", ""),
                "year": exp.get("year", "")
            }
            if source_info["source_id"] or source_info["title"]:
                self.add_source_instance(source_info)

        ontology = {
            "@context": {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "owl": "http://www.w3.org/2002/07/owl#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "pva": self.base
            },
            "@graph": self.graph
        }

        return ontology

    def to_turtle(self, ontology: dict = None) -> str:
        if ontology is None:
            ontology = {"@graph": self.graph}
        lines = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            f"@prefix pva: <{self.base}> .",
            "",
        ]
        for node in ontology.get("@graph", []):
            node_id = node.get("@id", "")
            node_type = node.get("@type", "")
            label = node.get("rdfs:label", "")
            if label:
                lines.append(f"<{node_id}> rdfs:label \"{label}\" .")
            if isinstance(node_type, str):
                lines.append(f"<{node_id}> a {node_type} .")
            for key, val in node.items():
                if key in ("@id", "@type", "rdfs:label"):
                    continue
                if isinstance(val, dict) and "@id" in val:
                    lines.append(f"<{node_id}> <{key}> <{val['@id']}> .")
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and "@id" in item:
                            lines.append(f"<{node_id}> <{key}> <{item['@id']}> .")
                        else:
                            lines.append(f"<{node_id}> <{key}> {json.dumps(item)} .")
                else:
                    lines.append(f"<{node_id}> <{key}> {json.dumps(val)} .")
            lines.append("")
        return "\n".join(lines)


import re


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build ontology from experiment data")
    parser.add_argument("--input", required=True, help="Path to normalized experiment data JSON")
    parser.add_argument("--output", required=True, help="Output path for ontology JSON")
    parser.add_argument("--format", choices=["jsonld", "turtle"], default="jsonld",
                        help="Output format")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    builder = OntologyBuilder(domain="pva_bopet")
    experiments = data.get("experiments", [])
    ontology = builder.build_from_experiments(experiments)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "jsonld":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ontology, f, indent=2, ensure_ascii=False)
    elif args.format == "turtle":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(builder.to_turtle(ontology))

    print(f"Ontology ({args.format}): {len(ontology.get('@graph', []))} elements -> {output_path}")


if __name__ == "__main__":
    main()