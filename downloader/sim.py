import json
import pandas as pd
import wget
import xarray

from datetime import date
from os import path
from utils import LOGGER, bar_progress


def get_data_info(source_key: str) -> dict:
    """
    Fonction pour récupérer les informations d'une source de données spécifiée.
    La source de données est représentée par sa clé (définie dans le fichier "conf/sim.json").

    :param source_key: Clé de la source de données désirée
    :return: Les informations de la source de données (nom du fichier, url de téléchargement)
    """
    if source_key is not None:
        with open("downloader/conf/conf.json", "r") as file:
            content = json.load(file)
            return content["sources"]["sim"][source_key]


def get_data_sources_name() -> list[str]:
    """
    Fonction pour récupérer l'ensemble des clés (source de données) présentent
    dans le fichier de configuration "conf/sim.json".

    :return: Une liste de clé
    """
    with open("downloader/conf/conf.json", "r") as file:
        content = json.load(file)
        return list(content["sources"]["sim"].keys())


def extract_years_from_data_source_name(data_source_name: str) -> list[int, int]:
    """
    Fonction pour extraire les années disponibles dans un fichier à
    partir de la clé d'une source de données.

    :param data_source_name: Clé de la source de données désirée
    :return: Un tableau avec l'année minimale et maximale
    """
    return [int(date) for date in data_source_name.split("_")[-2:]]


def get_required_data_source(start_date: date, end_date: date) -> list[str]:
    """
    Fonction pour sélectionner les sources de données nécessaires pour
    récupérer les données entre deux dates spécifiées.

    :param start_date: Date minimale
    :param end_date: Date maximale
    :return: Liste des sources de données à télécharger
    """
    min_year = start_date.year
    max_year = end_date.year

    data_sources_name = get_data_sources_name()
    file_to_dl = []

    for name in data_sources_name:
        curr_min, curr_max = extract_years_from_data_source_name(data_source_name=name)
        if min_year >= curr_min and min_year <= curr_max:
            file_to_dl.append(name)
        elif max_year <= curr_max and max_year >= curr_min:
            file_to_dl.append(name)

    return file_to_dl


def download_data(start_date: date, end_date: date) -> None:
    """
    Fonction globale pour télécharger les données.

    :param start_date: Date minimale
    :param end_date: Date maximale
    """
    data_sources_to_dl = get_required_data_source(
        start_date=start_date, end_date=end_date
    )

    for data_source in data_sources_to_dl:
        data_source_info = get_data_info(source_key=data_source)
        filename = data_source_info["filename"]

        if path.exists(f"downloader/data/{filename}"):
            LOGGER.info(f"Le fichier {filename} est déjà disponible localement.")

        else:
            LOGGER.info(f"Téléchargement du fichier {filename} en cours ...")
            wget.download(
                url=data_source_info["url"],
                out=f"downloader/data/{filename}",
                bar=bar_progress,
            )
            print()
            LOGGER.info(f"Téléchargement terminé !")


def get_data_from_file(filenames: list[str]) -> pd.DataFrame:
    """_summary_

    :param filename: _description_
    :return: _description_
    """
    df = pd.read_csv(filepath_or_buffer=filenames[0], compression="gzip", sep=";")

    if len(filenames) > 0:
        for i in range(1, len(filenames)):
            df = pd.concat(
                [
                    df,
                    pd.read_csv(
                        filepath_or_buffer=filenames[i], compression="gzip", sep=";"
                    ),
                ]
            )

    return df


def filter_dataframe(
    df: pd.DataFrame, vars: list[str], start_date: date, end_date: date
) -> pd.DataFrame:
    """_summary_

    :param df: _description_
    :param vars: _description_
    :param start_date: _description_
    :param end_date: _description_
    :return: _description_
    """
    # Variable filtering
    columns_to_keep = ["LAMBX", "LAMBY", "DATE"] + vars
    df = df[columns_to_keep].copy()

    # Date filtering
    df["DATE"] = pd.to_datetime(df["DATE"], format="%Y%m%d").dt.date
    df = df.loc[(df["DATE"] >= start_date) & (df["DATE"] <= end_date)]

    return df


def convert_df_to_netcdf(df: pd.DataFrame) -> xarray.core.dataset.Dataset:
    """_summary_

    :param df: _description_
    :return: _description_
    """
    df = df.set_index(["DATE", "LAMBX", "LAMBY"])
    return df.to_xarray()


def select_data_for_a_city(
    xarr: xarray.core.dataset.Dataset, city: str
) -> xarray.core.dataset.Dataset:
    """_summary_

    :param xarr: _description_
    :param city: _description_
    :return: _description_
    """
    city_mapping = {
        "montpellier": {"LAMBX": 7240, "LAMBY": 18490},
        "paris": {"LAMBX": 6040, "LMABY": 24250},
        "bordeaux": {"LAMBX": 3720, "LAMBY": 19850},
    }

    return xarr.sel(
        LAMBX=city_mapping[city]["LAMBX"], LAMBY=city_mapping[city]["LAMBY"]
    )


if __name__ == "__main__":
    # download_data(
    #     start_date=date(2019, 10, 20),
    #     end_date=date(2022, 10, 21)
    # )

    df = get_data_from_file(
        filenames=[
            # "downloader/data/QUOT_SIM2_2010-2019.csv.gz",
            "downloader/data/QUOT_SIM2_2020-2024.csv.gz",
        ]
    )
    print(df.head())
    print()

    df = filter_dataframe(
        df=df, vars=["T_Q"], start_date=date(2020, 1, 1), end_date=date(2020, 1, 2)
    )
    print(df.head())
    print()

    xarr = convert_df_to_netcdf(df=df)
    print(xarr)
    print()

    xarr = select_data_for_a_city(xarr=xarr, city="montpellier")
    print(xarr)
