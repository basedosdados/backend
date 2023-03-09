### TODO checar filtragem de todos os campos
### TODO rever observational_level, pede lista de id de colunas que atualmente n esta recebendo
#  https://staging.api.basedosdados.org/api/v1/graphql
#  https://staging.api.basedosdados.org/admin/

# "https://staging.backend.dados.rio/api/v1/graphql"


import json
from datetime import datetime
from ckan_django_utils import (
    Migration,
    get_token,
    get_package_model,
    get_bd_packages,
    parse_temporal_coverage,
)

from pathlib import Path
import pandas as pd


def get_credentials(mode):
    j = json.load(open("./credentials.json"))
    return j[mode]["username"], j[mode]["password"], j[mode]["url"]


migration_control = 1


def main(package_name_error=None, tables_error=[]):
    USERNAME, PASSWORD, URL = get_credentials("staging")
    TOKEN = get_token(URL, USERNAME, PASSWORD)
    m = Migration(url=URL, token=TOKEN)

    # id = "br-sgp-informacao"
    # id = "br-me-clima-organizacional"
    # df = get_package_model(name_or_id=id)
    df = get_bd_packages()
    df = df.head(50)
    entity_id = m.create_entity()
    update_frequency_id = m.create_update_frequency()
    # r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")
    count = 1
    for p, package_id in zip(df["packages"].tolist(), df["package_id"].tolist()):
        # create tags
        tags_ids = m.create_tags(objs=p.get("tags"))
        themes_ids = m.create_themes(objs=p.get("groups"))

        ## create organization
        print(
            "\n###############################################################################################\n\n",
            "Create Organization",
        )
        org_id = m.create_org(p.get("organization"))

        ## create dataset
        print(
            f"\nCreate Dataset: {count} - {p['name']} - {package_id}",
        )
        package_to_dataset = {
            "organization": org_id,
            "slug": p["name"].replace("-", "_"),
            "name": p["title"][:255],
            "description": p["notes"],
            "tags": tags_ids,
            "themes": themes_ids,
        }
        r, dataset_id = m.create_update(
            query_class="allDataset",
            query_parameters={"$slug: String": p["name"].replace("-", "_")},
            mutation_class="CreateUpdateDataset",
            mutation_parameters=package_to_dataset,
        )

        if package_name_error is not None and p["name"] != package_name_error:
            break

        for resource in p["resources"]:
            resource_type = resource["resource_type"]

            if (
                resource_type == "bdm_table"
                and resource["table_id"] not in tables_error
            ):

                print("\nCreate Table:", resource["table_id"])
                update_frequency_id = m.create_update_frequency(
                    observation_levels=resource["observation_level"],
                    update_frequency=resource["update_frequency"],
                )
                resource_to_table = {
                    "dataset": dataset_id,
                    "license": m.create_license(),
                    "partnerOrganization": m.create_org(
                        resource["partner_organization"]
                    ),
                    "updateFrequency": update_frequency_id,
                    "slug": resource["table_id"],
                    "name": resource["name"],
                    "pipeline": m.create_update(
                        query_class="allPipeline",
                        query_parameters={
                            "$githubUrl: String": "http://desconhecida.com"
                        },
                        mutation_class="CreateUpdatePipeline",
                        mutation_parameters={"githubUrl": "desconhecida.com"},
                    )[1],
                    "description": resource["description"],
                    "isDirectory": False,
                    "dataCleaningDescription": resource["data_cleaning_description"],
                    "dataCleaningCodeUrl": resource["data_cleaning_code_url"],
                    "rawDataUrl": resource["raw_files_url"],
                    "auxiliaryFilesUrl": resource["auxiliary_files_url"],
                    "architectureUrl": resource["architecture_url"],
                    "sourceBucketName": resource["source_bucket_name"],
                    "uncompressedFileSize": resource["uncompressed_file_size"],
                    "compressedFileSize": resource["compressed_file_size"],
                    "numberRows": 0,
                    "numberColumns": len(resource["columns"]),
                    "observationLevel": m.create_observation_level(
                        observation_levels=resource["observation_level"]
                    ),
                }

                r, table_id = m.create_update(
                    mutation_class="CreateUpdateTable",
                    mutation_parameters=resource_to_table,
                    query_class="allTable",
                    query_parameters={
                        "$slug: String": resource["table_id"],
                        "$name: String": resource["name"],
                        "$dataset_Id: ID": dataset_id,
                    },
                )
                m.create_coverage(resource=resource, coverage={"table": table_id})
                if "columns" in resource:
                    print("\nCreate Column")

                    columns_ids = m.create_columns(resource=resource, table_id=table_id)
                    resource_to_cloud_table = {
                        "table": table_id,
                        "gcpProjectId": resource["source_bucket_name"],
                        "gcpDatasetId": resource["dataset_id"],
                        "gcpTableId": resource["table_id"],
                        "columns": columns_ids,
                    }
                    print(
                        "\nCreate CloudTable:",
                        resource["dataset_id"] + "." + resource["table_id"],
                        "\n\n_______________________________________________________________________________________________",
                    )
                    r, cloud_table_id = m.create_update(
                        mutation_class="CreateUpdateCloudTable",
                        mutation_parameters=resource_to_cloud_table,
                        query_class="allCloudtable",
                        query_parameters={
                            "$gcpDatasetId: String": resource["dataset_id"],
                            "$gcpTableId: String": resource["table_id"],
                            "$table_Id: ID": table_id,
                        },
                    )

            elif resource_type == "external_link":
                print("\nCreate RawDataSource: ", resource["url"])
                resource_to_raw_data_source = {
                    "dataset": dataset_id,
                    # "coverages": "",
                    "availability": m.create_availability(resource),
                    # "languages": "",
                    "license": m.create_license(),
                    "updateFrequency": update_frequency_id,
                    "areaIpAddressRequired": m.create_area(area="desconhecida"),
                    # "createdAt": "",
                    # "updatedAt": "",
                    "url": resource["url"].replace(" ", ""),
                    "name": resource["name"],
                    "description": "TO DO"
                    if resource["description"] is None
                    else resource["description"],
                    # "containsStructureData": "",
                    # "containsApi": "",
                    # "isFree": "",
                    # "requiredRegistration": "",
                    # "entities": "",
                }

                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateRawDataSource",
                    mutation_parameters=resource_to_raw_data_source,
                    query_class="allRawdatasource",
                    query_parameters={
                        "$url: String": resource["url"].replace(" ", ""),
                        "$dataset_Id: ID": dataset_id,
                    },
                )
                m.create_coverage(
                    resource=resource, coverage={"rawDataSource": raw_source_id}
                )

            elif resource_type == "information_request":
                print("\nCreate InformationRequest: ", resource["name"])

                resource_to_information_request = {
                    "dataset": dataset_id,
                    "status": m.create_update(
                        query_class="allStatus",
                        query_parameters={
                            "$slug: String": resource["state"],
                        },
                        mutation_class="CreateUpdateStatus",
                        mutation_parameters={
                            "slug": resource["state"],
                            "name": resource["state"],
                        },
                    )[1],
                    "updateFrequency": update_frequency_id,
                    "origin": resource["origin"],
                    "slug": resource["name"]
                    .replace("/", "")
                    .replace("-", "")
                    .replace(".", ""),
                    "url": resource.get("data_url", ""),
                    "startedAt": datetime.strptime(
                        resource["opening_date"], "%d/%m/%Y"
                    ).strftime("%Y-%m-%d")
                    + "T00:00:00"
                    if "/" in resource["opening_date"]
                    else resource["opening_date"] + "T00:00:00",
                    "dataUrl": resource["url"],
                    "observations": resource.get("url", ""),
                    "startedBy": 1,
                    # "entities": "",
                }
                r, info_id = m.create_update(
                    mutation_class="CreateUpdateInformationRequest",
                    mutation_parameters=resource_to_information_request,
                    query_class="allInformationrequest",
                    query_parameters={
                        "$url: String": resource["url"],
                        "$dataset_Id: ID": dataset_id,
                    },
                    # update=True,
                )
                m.create_coverage(
                    resource=resource, coverage={"informationRequest": info_id}
                )
        print(
            "\n\n***********************************************************************************************\n\n"
        )
        if migration_control:
            path = Path("./utils/migration/data")
            path.mkdir(parents=True, exist_ok=True)

            file_path_migrated = path / "packages_migrated.csv"
            df_migrated = pd.DataFrame(data={"package_id": [package_id]})
            df_migrated.to_csv(
                file_path_migrated,
                index=False,
                mode="a",
                header=not file_path_migrated.exists(),
            )


if __name__ == "__main__":
    retry = 0
    while retry < 3:
        try:
            main(
                package_name_error=None,
                tables_error=[],
            )
        except Exception as e:
            retry += 1
            print(
                "\n\n\n\n************************************ Retry: ",
                retry,
                "************************************\n\n\n\n",
            )
            print(e)
