#!/usr/bin/env python3

"""Scan Azure AI Foundry / Azure OpenAI quota by region.



This script uses the Azure CLI login context. Run `az login` before using it.

"""



from __future__ import annotations



import argparse

import csv

import fnmatch

import json

import shutil

import subprocess

import sys

from pathlib import Path

from typing import Any





DEFAULT_REGIONS = [

    "eastus",

    "eastus2",

    "northcentralus",

    "southcentralus",

    "westus",

    "westus2",

    "westus3",

    "canadacentral",

    "canadaeast",

    "brazilsouth",

    "uksouth",

    "westeurope",

    "francecentral",

    "germanywestcentral",

    "norwayeast",

    "polandcentral",

    "swedencentral",

    "switzerlandnorth",

    "australiaeast",

    "japaneast",

    "koreacentral",

    "southeastasia",

    "centralindia",

    "southindia",

    "uaenorth",

    "southafricanorth",

]





FIELDNAMES = [

    "SubscriptionName",

    "SubscriptionId",

    "Region",

    "DeploymentType",

    "Model",

    "MetricName",

    "DisplayName",

    "Current",

    "Limit",

    "Available",

    "Unit",

]



AZ_COMMAND = "az"

NOT_MODEL_SPECIFIC = "(not model-specific)"

NOT_MODEL_SPECIFIC_METRICS = {

    "OpenAI.S0.AccountCount",

    "OpenAI.FineTuned.Deployments",

}





def parse_csv_argument(values: list[str] | None) -> list[str]:

    if not values:

        return []



    parsed: list[str] = []

    for value in values:

        parsed.extend(item.strip() for item in value.split(",") if item.strip())

    return parsed





def invoke_az_json(arguments: list[str], timeout_seconds: int | None = None) -> Any:

    command = [AZ_COMMAND, *arguments, "-o", "json"]

    try:

        completed = subprocess.run(

            command,

            capture_output=True,

            check=False,

            encoding="utf-8",

            errors="replace",

            timeout=timeout_seconds,

        )

    except subprocess.TimeoutExpired as exc:

        raise RuntimeError(

            f"az {' '.join(arguments)} timed out after {timeout_seconds} seconds"

        ) from exc



    if completed.returncode != 0:

        message = completed.stderr.strip() or completed.stdout.strip()

        raise RuntimeError(f"az {' '.join(arguments)} failed:\n{message}")



    output = completed.stdout.strip()

    if not output:

        return None



    return json.loads(output)





def invoke_az(arguments: list[str]) -> None:

    completed = subprocess.run(

        [AZ_COMMAND, *arguments],

        capture_output=True,

        check=False,

        encoding="utf-8",

        errors="replace",

    )

    if completed.returncode != 0:

        message = completed.stderr.strip() or completed.stdout.strip()

        raise RuntimeError(f"az {' '.join(arguments)} failed:\n{message}")





def get_account(subscription: str | None) -> dict[str, Any]:

    arguments = ["account", "show"]

    if subscription:

        arguments.extend(["--subscription", subscription])

    return invoke_az_json(arguments)





def get_all_physical_regions(subscription: str, active_subscription: str) -> list[str]:

    changed_subscription = subscription != active_subscription

    if changed_subscription:

        invoke_az(["account", "set", "--subscription", subscription])



    try:

        regions = invoke_az_json(

            [

                "account",

                "list-locations",

                "--query",

                "[?metadata.regionType=='Physical'].name",

            ]

        )

    finally:

        if changed_subscription:

            invoke_az(["account", "set", "--subscription", active_subscription])



    return list(regions or [])





def matches_model_filter(

    model_name: str,

    metric_name: str,

    display_name: str,

    model_filters: list[str],

) -> bool:

    if not model_filters:

        return True



    for model_filter in model_filters:

        has_wildcard = "*" in model_filter or "?" in model_filter

        if has_wildcard:

            if (

                fnmatch.fnmatchcase(model_name, model_filter)

                or fnmatch.fnmatchcase(metric_name, f"*{model_filter}*")

                or fnmatch.fnmatchcase(display_name, f"*{model_filter}*")

            ):

                return True

        elif model_name == model_filter or metric_name == model_filter:

            return True



    return False





def parse_usage_row(

    usage: dict[str, Any],

    region: str,

    subscription_name: str,

    subscription_id: str,

) -> dict[str, Any] | None:

    name = usage.get("name") or {}

    metric_name = str(name.get("value") or "")

    display_name = str(name.get("localizedValue") or "")



    if not metric_name.startswith("OpenAI."):

        return None



    parts = metric_name.split(".")

    deployment_type = parts[1] if len(parts) >= 2 else ""

    is_model_specific = len(parts) >= 3 and metric_name not in NOT_MODEL_SPECIFIC_METRICS

    model = ".".join(parts[2:]) if is_model_specific else NOT_MODEL_SPECIFIC



    current = float(usage.get("currentValue") or 0)

    limit = float(usage.get("limit") or 0)

    available = max(0.0, limit - current)



    return {

        "SubscriptionName": subscription_name,

        "SubscriptionId": subscription_id,

        "Region": region,

        "DeploymentType": deployment_type,

        "Model": model,

        "MetricName": metric_name,

        "DisplayName": display_name,

        "Current": current,

        "Limit": limit,

        "Available": available,

        "Unit": usage.get("unit") or "",

    }





def format_table(rows: list[dict[str, Any]], limit: int = 80) -> str:

    columns = ["Region", "DeploymentType", "Model", "Current", "Limit", "Available", "DisplayName"]

    display_rows = rows[:limit]

    widths = {

        column: max(

            len(column),

            *(len(str(row.get(column, ""))) for row in display_rows),

        )

        for column in columns

    }



    lines = ["  ".join(column.ljust(widths[column]) for column in columns)]

    lines.append("  ".join("-" * widths[column] for column in columns))

    for row in display_rows:

        lines.append("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))



    if len(rows) > limit:

        lines.append(f"... {len(rows) - limit} more rows not shown. Use CSV/JSON output for the full report.")



    return "\n".join(lines)





def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:

    with path.open("w", newline="", encoding="utf-8") as output:

        writer = csv.DictWriter(output, fieldnames=FIELDNAMES)

        writer.writeheader()

        writer.writerows(rows)





def write_json(path: Path, rows: list[dict[str, Any]]) -> None:

    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")





def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        description="Scan Azure AI Foundry / Azure OpenAI quota by region."

    )

    parser.add_argument("--subscription", help="Azure subscription name or ID.")

    parser.add_argument(

        "--regions",

        action="append",

        help="Comma-separated regions to scan, for example: eastus,swedencentral.",

    )

    parser.add_argument(

        "--models",

        action="append",

        help="Comma-separated model names. Exact by default; use quotes for wildcards, for example 'gpt-4o*'.",

    )

    parser.add_argument(

        "--all-physical-regions",

        action="store_true",

        help="Scan every physical Azure region returned by az account list-locations.",

    )

    parser.add_argument(

        "--show-zero-quota",

        action="store_true",

        help="Include rows where available quota is zero.",

    )

    parser.add_argument(

        "--model-specific-only",

        action="store_true",

        help="Hide account-level quota rows that are not tied to one model.",

    )

    parser.add_argument("--csv-path", help="Write results to this CSV file.")

    parser.add_argument("--json-path", help="Write results to this JSON file.")

    parser.add_argument(

        "--region-timeout-seconds",

        type=int,

        default=45,

        help="Timeout for each regional quota API call. Default: 45.",

    )

    return parser





def main() -> int:

    global AZ_COMMAND



    parser = build_parser()

    args = parser.parse_args()



    az_command = shutil.which("az")

    if not az_command:

        print("Azure CLI was not found. Install it and run az login.", file=sys.stderr)

        return 1

    AZ_COMMAND = az_command



    model_filters = parse_csv_argument(args.models)

    regions = parse_csv_argument(args.regions) or DEFAULT_REGIONS



    try:

        account = get_account(args.subscription)

        subscription_id = args.subscription or account["id"]



        if args.all_physical_regions:

            regions = get_all_physical_regions(subscription_id, account["id"])



        results: list[dict[str, Any]] = []

        failures: list[dict[str, str]] = []



        for region in sorted(set(regions)):

            print(f"Checking {region}...", flush=True)

            try:

                usages = invoke_az_json(

                    [

                        "cognitiveservices",

                        "usage",

                        "list",

                        "--location",

                        region,

                        "--subscription",

                        subscription_id,

                    ],

                    timeout_seconds=args.region_timeout_seconds,

                )

            except RuntimeError as exc:

                failures.append({"Region": region, "Error": str(exc)})

                continue



            for usage in usages or []:

                row = parse_usage_row(

                    usage,

                    region,

                    account.get("name", ""),

                    subscription_id,

                )

                if not row:

                    continue



                if args.model_specific_only and row["Model"] == NOT_MODEL_SPECIFIC:

                    continue



                if not matches_model_filter(

                    row["Model"], row["MetricName"], row["DisplayName"], model_filters

                ):

                    continue



                if not args.show_zero_quota and float(row["Available"]) <= 0:

                    continue



                results.append(row)



        results.sort(key=lambda row: (row["Model"], row["DeploymentType"], row["Region"]))



        if args.csv_path:

            write_csv(Path(args.csv_path), results)

            print(f"CSV written to {args.csv_path}")



        if args.json_path:

            write_json(Path(args.json_path), results)

            print(f"JSON written to {args.json_path}")



        if results:

            print(format_table(results))

        else:

            print(

                "No matching quota with available capacity was found. "

                "Re-run with --show-zero-quota to see zero-quota rows.",

                file=sys.stderr,

            )



        if failures:

            print("\nSome regions could not be checked:", file=sys.stderr)

            for failure in failures:

                print(f"- {failure['Region']}: {failure['Error']}", file=sys.stderr)



        return 0

    except RuntimeError as exc:

        print(str(exc), file=sys.stderr)

        return 1





if __name__ == "__main__":

    raise SystemExit(main())