import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#chargement des données
try:
    data = pd.read_excel("online_retail.xlsx")
    print("Fichier chargé avec succès!")
    print(f"Nombre de lignes: {len(data)}")
    print(f"Nombre de colonnes: {len(data.columns)}")
    print("\nPremières lignes:")
    print(data.head())
    print("\nInformations sur les colonnes:")
    data.info()
except FileNotFoundError:
    print("Erreur: fichier 'online_retail.xlsx' introuvable")
except Exception as e:
    print(f"Erreur lors du chargement: {e}")


