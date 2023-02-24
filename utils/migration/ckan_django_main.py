### TODO fazer coverage para os trez tipos de recurso utilizando parse_temporal_coverage
### TODO filtrar pelo id do modelo pai
### TODO usar dataframe para controle dos packages, coluna migrate 'e alterada para 1 quando o package 'e migrado

import json
from datetime import datetime
from ckan_django_utils import (
    Migration,
    get_token,
    get_package_model,
    get_bd_packages,
    parse_temporal_coverage,
)


j = json.load(open("./credentials.json"))
USERNAME = j["username"]
PASSWORD = j["password"]


if __name__ == "__main__":
    TOKEN = get_token(USERNAME, PASSWORD)
    # id = 'br-sgp-informacao'
    # id = "br-me-clima-organizacional"
    # packages = [get_package_model(id=id)]

    packages = get_bd_packages()

    m = Migration(TOKEN)
    entity_id = m.create_entity()
    update_frequency_id = m.create_update_frequency()
    # r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")
    for p in packages:
        # create tags
        tags_ids = m.create_tags(objs=p.get("tags"))
        themes_ids = m.create_themes(objs=p.get("groups"))

        ## create organization

        print("\nCreate Organization")
        org_slug = p.get("organization").get("name").replace("-", "_")
        package_to_org = {
            "area": m.create_update(
                query_class="allArea",
                query_parameters={"$slug: String": "desconhecida"},
                mutation_class="CreateUpdateArea",
                mutation_parameters={"slug": "desconhecida"},
            )[1],
            "slug": org_slug,
            "name": p.get("organization").get("title"),
            "description": p.get("organization").get("description"),
        }
        r, org_id = m.create_update(
            query_class="allOrganization",
            query_parameters={"$slug: String": org_slug},
            mutation_class="CreateUpdateOrganization",
            mutation_parameters=package_to_org,
        )

        ## create dataset
        print("\nCreate Dataset")
        package_to_dataset = {
            "organization": org_id,
            "slug": p["name"].replace("-", "_")[:49],
            "name": p["title"],
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

        for resource in p["resources"]:
            resource_type = resource["resource_type"]

            if resource_type == "bdm_table":
                print("\nCreate Table")

                update_frequency_id = m.create_update_frequency(
                    observation_levels=resource["observation_level"],
                    update_frequency=resource["update_frequency"],
                )
                resource_to_table = {
                    "dataset": dataset_id,
                    "license": m.create_license(),
                    "partnerOrganization": m.create_part_org(
                        resource["partner_organization"]
                    ),
                    "updateFrequency": update_frequency_id,
                    "slug": resource["table_id"],
                    "name": resource["name"],
                    "pipeline": m.create_update(
                        query_class="allPipeline",
                        query_parameters={"$githubUrl: String": "todo.com"},
                        mutation_class="CreateUpdatePipeline",
                        mutation_parameters={"githubUrl": "todo.com"},
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
                    },
                )
                if "columns" in resource:
                    print("\nCreate Column")
                    columns_ids = m.create_columns(
                        objs=resource.get("columns"), table_id=table_id
                    )

                    resource_to_cloud_table = {
                        "table": table_id,
                        "gcpProjectId": resource["source_bucket_name"],
                        "gcpDatasetId": resource["dataset_id"],
                        "gcpTableId": resource["table_id"],
                        "columns": columns_ids,
                    }
                    print("\nCreate CloudTable")
                    r, cloud_table_id = m.create_update(
                        mutation_class="CreateUpdateCloudTable",
                        mutation_parameters=resource_to_cloud_table,
                        query_class="allCloudtable",
                        query_parameters={
                            "$gcpDatasetId: String": resource["dataset_id"],
                            "$gcpTableId: String": resource["table_id"],
                        },
                    )

            elif resource_type == "external_link":

                print("\nCreate RawDataSource")
                resource_to_raw_data_source = {
                    "dataset": dataset_id,
                    # "coverages": "",
                    "availability": m.create_availability(resource),
                    # "languages": "",
                    "license": m.create_license(),
                    "updateFrequency": update_frequency_id,
                    "areaIpAddressRequired": m.create_update(
                        query_class="allArea",
                        query_parameters={"$slug: String": "desconhecida"},
                        mutation_class="CreateUpdateArea",
                        mutation_parameters={"slug": "desconhecida"},
                    )[1],
                    # "createdAt": "",
                    # "updatedAt": "",
                    "url": resource["url"],
                    "name": resource["name"],
                    "description": "TO DO"
                    if resource["description"] is None
                    else resource["description"],
                    # "containsStructureData": "",
                    # "containsApi": "",
                    # "isFree": "",
                    # "requiredRegistration": "",
                    # "observationLevel": "",
                }

                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateRawDataSource",
                    mutation_parameters=resource_to_raw_data_source,
                    query_class="allRawdatasource",
                    query_parameters={"$url: String": resource["url"]},
                )

                print(r)

            elif resource_type == "information_request":
                print("\nCreate InformationRequest")

                resource_to_information_request = {
                    "dataset": dataset_id,
                    "status": m.create_update(
                        query_class="allStatus",
                        query_parameters={"$slug: String": resource["state"]},
                        mutation_class="CreateUpdateStatus",
                        mutation_parameters={
                            "slug": resource["state"],
                            "name": resource["state"],
                        },
                    )[1],
                    "updateFrequency": update_frequency_id,
                    "origin": resource["origin"],
                    "slug": resource["name"],
                    "url": resource["url"],
                    "startedAt": datetime.strptime(
                        resource["opening_date"], "%d/%m/%Y"
                    ).strftime("%Y-%m-%d")
                    + "T00:00:00"
                    if "/" in resource["opening_date"]
                    else resource["opening_date"] + "T00:00:00",
                    "dataUrl": resource["data_url"],
                    "observations": resource["department"],
                    "startedBy": 1,
                    # "observationLevel": "",
                }
                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateInformationRequest",
                    mutation_parameters=resource_to_information_request,
                    query_class="allInformationrequest",
                    query_parameters={"$url: String": resource["url"]},
                )
                print(r)

        # df.loc[0,'migrate'] = 1
