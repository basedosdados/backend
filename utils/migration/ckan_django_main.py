### TODO rever observational_level, pede lista de id de colunas que atualmente n esta recebendo


#  https://staging.api.basedosdados.org/api/v1/graphql
#  https://staging.api.basedosdados.org/admin/


# "https://staging.backend.dados.rio/api/v1/graphql"


import json
from datetime import datetime
import pandas as pd
from ckan_django_utils import (
    Migration,
    class_to_dict,
    get_bd_packages,
)
from data.enums.language import LanguageEnum


from pathlib import Path
import pandas as pd


def main(
    mode="local",
    migrate_enum=True,
    migration_control=True,
    package_name_error=None,
    tables_error=[],
):
    m = Migration(mode=mode)
    m.create_enum(migrate_enum)

    # id = "br-sgp-informacao"
    # id = "br-me-clima-organizacional"
    # df = get_package_model(name_or_id=id)
    df = get_bd_packages()
    # r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")
    count = 1
    for p, package_id in zip(df["packages"].tolist(), df["package_id"].tolist()):
        # create tags
        themes_ids = m.create_themes(objs=p.get("groups"))
        tags_ids = m.create_tags(objs=p.get("tags"))

        ## create organization
        print(
            "\n###############################################################################################\n\n",
            "Create Organization",
        )
        org_id, dataset_remove_prefix = m.create_org(p.get("organization"))
        dataset_slug = p["name"].replace("-", "_")
        if dataset_remove_prefix is not None and dataset_remove_prefix in dataset_slug:
            dataset_slug = dataset_slug.replace(dataset_remove_prefix, "")

        ## create dataset
        print(
            f"\nCreate Dataset: {count} - {p['name']} - {dataset_slug} - {package_id}",
        )
        package_to_dataset = {
            "organization": org_id,
            "slug": dataset_slug,
            "name": p["title"][:255],
            "description": p["notes"],
            "tags": tags_ids,
            "themes": themes_ids,
        }
        r, dataset_id = m.create_update(
            query_class="allDataset",
            query_parameters={
                "$slug: String": dataset_slug,
                "$organization_Id: ID": org_id,
            },
            mutation_class="CreateUpdateDataset",
            mutation_parameters=package_to_dataset,
        )

        if package_name_error is not None and p["name"] != package_name_error:
            raise Exception("Package name error")

        for resource in p["resources"]:
            resource_type = resource["resource_type"]

            if (
                resource_type == "bdm_table"
                and resource["table_id"] not in tables_error
            ):

                print("\nCreate Table:", resource["table_id"])
                resource_to_table = {
                    "dataset": dataset_id,
                    "license": m.create_license(
                        obj={"slug": "desconhecida", "name": "desconhecida"}
                    ),
                    "partnerOrganization": m.create_org(
                        resource["partner_organization"]
                    )[0],
                    "updateFrequency": m.create_update_frequency(
                        observation_levels=resource.get("observation_level", None),
                        update_frequency=resource.get("update_frequency", None),
                    ),
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
                        observation_levels=resource["observation_level"],
                    ),
                    # "publishedBy":resource.get("published_by",{}).get("name",None),
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
                ### update observation level
                m.create_observation_level(
                    observation_levels=resource["observation_level"],
                    table_id=table_id,
                )

                # pass

            elif resource_type == "external_link":
                print("\nCreate RawDataSource: ", resource["url"])

                languages_ids = []
                languages = class_to_dict(LanguageEnum())

                for lang in resource.get("language", []):

                    languages_ids.append(
                        m.create_language(
                            {
                                "slug": languages.get(lang, {}).get("abrev", None),
                                "name": languages.get(lang, {}).get("label", None),
                            }
                        )
                    )

                resource_to_raw_data_source = {
                    "dataset": dataset_id,
                    # "coverages": "",
                    "availability": m.create_availability(resource),
                    "languages": languages_ids,
                    "license": m.create_license(
                        obj={
                            "slug": resource.get("license", "unknown"),
                            "name": resource.get("license", "Desconhecida"),
                        }
                    ),
                    "updateFrequency": m.create_update_frequency(
                        observation_levels=resource.get("observation_level", None),
                        update_frequency=resource.get("update_frequency", None),
                    ),
                    # "areaIpAddressRequired": m.create_area(obj="desconhecida"),
                    # "createdAt": "",
                    # "updatedAt": "",
                    "url": resource["url"].replace(" ", ""),
                    "name": resource["name"],
                    "description": "TO DO"
                    if resource["description"] is None
                    else resource["description"],
                    "containsStructureData": resource.get("has_structured_data ", None)
                    == "yes",
                    "containsApi": resource.get("has_api", None) == "yes",
                    "isFree": resource.get("is_free", None) == "yes",
                    "requiredRegistration": resource.get("requires_registration", None)
                    == "yes",
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
                    "updateFrequency": m.create_update_frequency(
                        observation_levels=resource.get("observation_level", None),
                        update_frequency=resource.get("update_frequency", None),
                    ),
                    "origin": resource["origin"],
                    "number": resource["name"],
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
    main(
        mode="local",
        migrate_enum={
            "AvailabilityEnum": False,
            "LicenseEnum": False,
            "LanguageEnum": True,
            "StatusEnum": False,
            "BigQueryTypeEnum": False,
            "EntityEnum": False,
            "AreaEnum": False,
        },
        migration_control=True,
        package_name_error=None,
        tables_error=[],
    )

    # retry = 0
    # while retry < 3:
    #     try:
    #         main(
    #             mode="staging",
    #             migrate_enum=True,
    #             package_name_error=None,
    #             tables_error=[],
    #         )
    #     except Exception as e:
    #         retry += 1
    #         print(
    #             "\n\n\n\n************************************ Retry: ",
    #             retry,
    #             "************************************\n\n\n\n",
    #         )
    #         print(e, "\n\n\n\n")
