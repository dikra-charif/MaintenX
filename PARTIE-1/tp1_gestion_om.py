import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

FICHIER = 'oms.csv'
COLONNES = ['ref_om', 'ref_equipement', 'designation',
            'ref_maintenancier', 'cout', 'date_fin']
LIBELLES = {
    'ref_om': 'Référence OM',
    'ref_equipement': 'Référence équipement',
    'designation': 'Désignation',
    'ref_maintenancier': 'Référence maintenancier',
    'cout': 'Coût',
    'date_fin': 'Date de fin (JJ/MM/AAAA)',
}


class ErreurSource(Exception):
    pass


class ErreurValidation(Exception):
    pass


class GestionnaireOM:

    def __init__(self, chemin=FICHIER):
        self.chemin = chemin

    def lire(self):
        if not os.path.exists(self.chemin):
            self._ecrire([])
        try:
            with open(self.chemin, newline='', encoding='utf-8-sig') as f:
                return list(csv.DictReader(f, delimiter=';'))
        except (OSError, csv.Error) as e:
            raise ErreurSource(
                f'Connexion à la source de données échouée : {e}')

    def _ecrire(self, lignes):
        try:
            with open(self.chemin, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=';')
                w.writeheader()
                w.writerows(lignes)
        except OSError as e:
            raise ErreurSource(
                f'Écriture impossible (fichier ouvert dans Excel ?) : {e}')

    @staticmethod
    def valider(om):
        for col in COLONNES:
            if not str(om.get(col, '')).strip():
                raise ErreurValidation(
                    'Tous les champs doivent être renseignés.')
        try:
            float(om['cout'].replace(',', '.'))
        except ValueError:
            raise ErreurValidation('Le coût doit être un nombre.')
        try:
            datetime.strptime(om['date_fin'], '%d/%m/%Y')
        except ValueError:
            raise ErreurValidation(
                'La date doit respecter le format JJ/MM/AAAA.')

    def ajouter(self, om):
        self.valider(om)
        lignes = self.lire()
        if any(l['ref_om'] == om['ref_om'] for l in lignes):
            raise ErreurValidation('Cette référence existe déjà.')
        lignes.append(om)
        self._ecrire(lignes)

    def modifier(self, om):
        self.valider(om)
        lignes = self.lire()
        for i, l in enumerate(lignes):
            if l['ref_om'] == om['ref_om']:
                lignes[i] = om
                self._ecrire(lignes)
                return
        raise ErreurValidation('Aucun OM ne porte cette référence.')

    def supprimer(self, ref):
        lignes = self.lire()
        restantes = [l for l in lignes if l['ref_om'] != ref]
        if len(restantes) == len(lignes):
            raise ErreurValidation('Aucun OM ne porte cette référence.')
        self._ecrire(restantes)

    def rechercher(self, ref):
        for l in self.lire():
            if l['ref_om'] == ref:
                return l
        return None


class Application(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('Gestion des ordres de maintenance')
        self.geometry('1050x560')
        self.gestionnaire = GestionnaireOM()
        self._construire_interface()
        self._executer(self.afficher)

    def _construire_interface(self):
        tk.Label(self, text='Gestion des ordres de maintenance',
                 font=('Arial', 16, 'bold'), bg='black',
                 fg='white', pady=10).pack(fill='x')
        corps = tk.Frame(self)
        corps.pack(fill='both', expand=True, padx=10, pady=10)
        gauche = tk.Frame(corps)
        gauche.pack(side='left', fill='both', expand=True)
        droite = tk.Frame(corps)
        droite.pack(side='right', fill='y', padx=(10, 0))

        formulaire = tk.Frame(gauche)
        formulaire.pack(fill='x')
        self.champs = {}
        for i, col in enumerate(COLONNES):
            tk.Label(formulaire, text=LIBELLES[col],
                     anchor='w').grid(row=i, column=0, sticky='w', pady=2)
            e = tk.Entry(formulaire, width=35)
            e.grid(row=i, column=1, padx=10)
            self.champs[col] = e

        self.tableau = ttk.Treeview(gauche, columns=COLONNES,
                                    show='headings', height=12)
        for col in COLONNES:
            self.tableau.heading(col, text=LIBELLES[col])
            self.tableau.column(col, width=130)
        self.tableau.pack(fill='both', expand=True, pady=10)
        self.tableau.bind('<<TreeviewSelect>>',
                          lambda ev: self._executer(self._sur_selection))

        boutons = [('Ajouter', self.ajouter), ('Afficher', self.afficher),
                   ('Modifier', self.modifier),
                   ('Supprimer', self.supprimer),
                   ('Rechercher', self.rechercher),
                   ('Réinitialiser', self.reinitialiser),
                   ('Quitter', self.destroy)]
        for texte, action in boutons:
            tk.Button(droite, text=texte, width=14, height=2,
                      command=lambda a=action: self._executer(a)).pack(pady=3)

    def _executer(self, action):
        try:
            action()
        except ErreurValidation as e:
            messagebox.showwarning('Données invalides', str(e))
        except ErreurSource as e:
            messagebox.showerror('Erreur de source de données', str(e))
        except Exception as e:
            messagebox.showerror('Erreur inattendue', str(e))

    def _lire_champs(self):
        return {col: self.champs[col].get().strip() for col in COLONNES}

    def _remplir_champs(self, om):
        for col in COLONNES:
            self.champs[col].delete(0, 'end')
            self.champs[col].insert(0, om[col])

    def _vider_champs(self):
        for e in self.champs.values():
            e.delete(0, 'end')

    def _sur_selection(self):
        sel = self.tableau.selection()
        if not sel:
            return
        om = self.gestionnaire.rechercher(sel[0])
        if om:
            self._remplir_champs(om)

    def afficher(self, lignes=None):
        if lignes is None:
            lignes = self.gestionnaire.lire()
        self.tableau.delete(*self.tableau.get_children())
        for l in lignes:
            self.tableau.insert('', 'end', iid=l['ref_om'],
                                values=[l[c] for c in COLONNES])

    def ajouter(self):
        self.gestionnaire.ajouter(self._lire_champs())
        self.afficher()
        self._vider_champs()
        messagebox.showinfo('Succès', 'OM ajouté avec succès.')

    def modifier(self):
        self.gestionnaire.modifier(self._lire_champs())
        self.afficher()
        messagebox.showinfo('Succès', 'OM modifié avec succès.')

    def supprimer(self):
        ref = self.champs['ref_om'].get().strip()
        if not ref:
            raise ErreurValidation(
                'Sélectionnez ou saisissez la référence de l\'OM à supprimer.')
        if messagebox.askyesno('Confirmation',
                               f'Supprimer l\'OM {ref} ?'):
            self.gestionnaire.supprimer(ref)
            self.afficher()
            self._vider_champs()

    def rechercher(self):
        ref = self.champs['ref_om'].get().strip()
        if not ref:
            raise ErreurValidation('Saisissez la référence à rechercher.')
        om = self.gestionnaire.rechercher(ref)
        if om is None:
            messagebox.showinfo('Recherche', 'Aucun OM trouvé.')
        else:
            self.afficher([om])
            self._remplir_champs(om)

    def reinitialiser(self):
        self._vider_champs()
        self.afficher()


if __name__ == '__main__':
    Application().mainloop()
