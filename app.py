"""
Application Principale - Plateforme Num_Exam
Interface multi-acteurs pour la gestion des emplois du temps d'examens
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import sys
import os

import streamlit as st
from supabase import create_client

SUPABASE_URL = "https://kwywfonvzzeplkaqbnfm.supabase.co"   # from step 2
SUPABASE_KEY = "sb_publishable_dw_zxmgmTjuEvcBSrgsgDg_vvgQHNV2"       # from step 2
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test connection
data = supabase.table("users").select("*").execute()
st.write(data)



# Ajouter le répertoire src au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db_connection import db

# Configuration de la page
st.set_page_config(
    page_title="Num_Exam - Gestion des Examens",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialiser les variables de session"""
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'session_exam_id' not in st.session_state:
        st.session_state.session_exam_id = 1

def show_login():
    """Afficher l'écran de connexion/sélection de rôle"""
    st.markdown('<div class="main-header">🎓 Plateforme Num_Exam</div>', unsafe_allow_html=True)
    st.markdown("### Gestion Intelligente des Emplois du Temps d'Examens")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("#### 👤 Sélectionnez votre profil")
        
        role = st.selectbox(
            "Rôle",
            ["", "Vice-Doyen", "Administrateur Examens", "Chef de Département", "Étudiant", "Professeur"],
            index=0
        )
        
        if role == "Étudiant":
            st.info("ℹ️ Les étudiants peuvent consulter les emplois du temps sans connexion")
            if st.button("📅 Voir les emplois du temps", type="primary"):
                st.session_state.role = "Étudiant"
                st.session_state.user_id = None  # Pas d'ID requis
                st.rerun()
        
        elif role == "Professeur":
            # Recherche de professeur
            search = st.text_input("🔍 Rechercher par nom ou prénom")
            
            if search and len(search) >= 3:
                profs = db.execute_to_dataframe("""
                    SELECT p.id, p.matricule, p.nom, p.prenom, d.nom as departement
                    FROM professeurs p
                    JOIN departements d ON p.dept_id = d.id
                    WHERE p.nom ILIKE %s OR p.prenom ILIKE %s
                    LIMIT 10
                """, (f"%{search}%", f"%{search}%"))
                
                if not profs.empty:
                    prof_options = [
                        f"{row['matricule']} - {row['nom']} {row['prenom']} ({row['departement']})"
                        for _, row in profs.iterrows()
                    ]
                    selected = st.selectbox("Sélectionnez votre profil", prof_options)
                    
                    if st.button("Se connecter", type="primary"):
                        idx = prof_options.index(selected)
                        st.session_state.role = "Professeur"
                        st.session_state.user_id = profs.iloc[idx]['id']
                        st.session_state.user_name = f"{profs.iloc[idx]['prenom']} {profs.iloc[idx]['nom']}"
                        st.rerun()
                else:
                    st.info("Aucun professeur trouvé")
        
        elif role == "Chef de Département":
            # Sélection du département
            depts = db.get_departments()
            dept_options = [f"{row['code']} - {row['nom']}" for _, row in depts.iterrows()]
            selected_dept = st.selectbox("Sélectionnez votre département", dept_options)
            
            if st.button("Se connecter", type="primary"):
                idx = dept_options.index(selected_dept)
                st.session_state.role = "Chef de Département"
                st.session_state.user_id = depts.iloc[idx]['id']
                st.session_state.user_name = f"Chef {depts.iloc[idx]['nom']}"
                st.rerun()
        
        elif role in ["Vice-Doyen", "Administrateur Examens"]:
            if st.button("Se connecter", type="primary"):
                st.session_state.role = role
                st.session_state.user_id = 1  # Admin ID
                st.session_state.user_name = role
                st.rerun()

def show_student_interface():
    """Interface publique pour consulter les emplois du temps"""
    st.sidebar.markdown("### 📅 Consultation Publique")
    st.sidebar.markdown("**Accès:** Étudiant")
    
    if st.sidebar.button("🔙 Retour à l'accueil"):
        st.session_state.role = None
        st.rerun()
    
    st.markdown('<div class="main-header">📅 Emplois du Temps des Examens</div>', unsafe_allow_html=True)
    
    st.markdown("### 🔍 Filtrer les examens")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        depts = db.get_departments()
        dept_options = ["Tous"] + [f"{row['code']} - {row['nom']}" for _, row in depts.iterrows()]
        selected_dept = st.selectbox("Département", dept_options)
    
    with col2:
        if selected_dept != "Tous":
            dept_idx = dept_options.index(selected_dept) - 1
            dept_id = depts.iloc[dept_idx]['id']
            formations = db.get_formations_by_department(dept_id)
            formation_options = ["Toutes"] + formations['nom'].tolist()
        else:
            formations = db.execute_to_dataframe("SELECT DISTINCT nom FROM formations ORDER BY nom")
            formation_options = ["Toutes"] + formations['nom'].tolist()
        
        selected_formation = st.selectbox("Formation", formation_options)
    
    with col3:
        dates = db.execute_to_dataframe("""
            SELECT DISTINCT date_examen 
            FROM examens 
            WHERE session_id = 1 
            ORDER BY date_examen
        """)
        date_options = ["Toutes"] + [d.strftime('%d/%m/%Y') for d in dates['date_examen']]
        selected_date = st.selectbox("Date", date_options)
    
    # Construire la requête selon les filtres
    query = """
        SELECT 
            e.date_examen,
            e.heure_debut,
            e.duree_minutes,
            m.code as code_module,
            m.nom as nom_module,
            f.nom as formation,
            d.nom as departement,
            l.nom as lieu,
            CONCAT(p.nom, ' ', p.prenom) as surveillant
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        JOIN departements d ON f.dept_id = d.id
        LEFT JOIN lieux_examen l ON e.lieu_id = l.id
        LEFT JOIN professeurs p ON e.prof_surveillant_id = p.id
        WHERE e.session_id = 1
    """
    params = []
    
    if selected_dept != "Tous":
        query += " AND d.id = %s"
        params.append(dept_id)
    
    if selected_formation != "Toutes":
        query += " AND f.nom = %s"
        params.append(selected_formation)
    
    if selected_date != "Toutes":
        date_obj = datetime.strptime(selected_date, '%d/%m/%Y').date()
        query += " AND e.date_examen = %s"
        params.append(date_obj)
    
    query += " ORDER BY e.date_examen, e.heure_debut"
    
    schedule = db.execute_to_dataframe(query, tuple(params) if params else None)
    
    if schedule.empty:
        st.info("🔭 Aucun examen trouvé avec ces critères")
    else:
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 Nombre d'examens", len(schedule))
        with col2:
            dates_uniques = schedule['date_examen'].nunique()
            st.metric("📅 Jours d'examens", dates_uniques)
        with col3:
            formations_uniques = schedule['formation'].nunique()
            st.metric("🎓 Formations", formations_uniques)
        
        st.markdown("---")
        
        # Tableau du planning
        st.markdown("### 📋 Planning détaillé")
        
        display_schedule = schedule.copy()
        display_schedule['Date'] = pd.to_datetime(display_schedule['date_examen']).dt.strftime('%d/%m/%Y')
        display_schedule['Heure'] = display_schedule['heure_debut'].astype(str)
        display_schedule['Durée'] = display_schedule['duree_minutes'].astype(str) + ' min'
        
        st.dataframe(
            display_schedule[['Date', 'Heure', 'Durée', 'code_module', 'nom_module', 
                            'formation', 'departement', 'lieu', 'surveillant']],
            use_container_width=True,
            hide_index=True
        )
        
        # Vue calendrier
        st.markdown("### 📆 Vue Calendrier")
        
        fig = px.timeline(
            schedule,
            x_start='date_examen',
            x_end='date_examen',
            y='formation',
            color='departement',
            hover_data=['code_module', 'lieu', 'heure_debut'],
            title="Répartition des examens"
        )
        st.plotly_chart(fig, use_container_width=True)

def show_professor_interface():
    """Interface pour les professeurs - LECTURE SEULE"""
    st.sidebar.markdown(f"### 👨‍🏫 {st.session_state.user_name}")
    st.sidebar.markdown(f"**Rôle:** Professeur")
    
    if st.sidebar.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown('<div class="main-header">📋 Mes Surveillances d\'Examens</div>', unsafe_allow_html=True)
    
    # Récupérer le planning de surveillance
    schedule = db.get_professor_schedule(st.session_state.user_id, st.session_state.session_exam_id)
    
    if schedule.empty:
        st.info("🔭 Aucune surveillance planifiée pour le moment")
    else:
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👁️ Nombre de surveillances", len(schedule))
        with col2:
            dates_uniques = schedule['date_examen'].nunique()
            st.metric("📅 Jours de surveillance", dates_uniques)
        with col3:
            max_par_jour = schedule.groupby('date_examen').size().max()
            st.metric("📊 Maximum par jour", int(max_par_jour))
        
        st.markdown("---")
        
        # Tableau des surveillances
        st.markdown("### 📋 Planning de surveillance")
        
        display_schedule = schedule.copy()
        display_schedule['Date'] = pd.to_datetime(display_schedule['date_examen']).dt.strftime('%d/%m/%Y')
        display_schedule['Heure'] = display_schedule['heure_debut'].astype(str)
        display_schedule['Durée'] = display_schedule['duree_minutes'].astype(str) + ' min'
        
        st.dataframe(
            display_schedule[['Date', 'Heure', 'Durée', 'code_module', 'formation', 'lieu', 'nb_inscrits']],
            use_container_width=True,
            hide_index=True
        )
        
        # Graphique de répartition
        st.markdown("### 📊 Répartition par jour")
        
        daily_count = schedule.groupby('date_examen').size().reset_index(name='Nombre de surveillances')
        
        fig = px.bar(
            daily_count,
            x='date_examen',
            y='Nombre de surveillances',
            title="Nombre de surveillances par jour"
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    """Fonction principale"""
    init_session_state()
    
    # Si non connecté, afficher l'écran de connexion
    if st.session_state.role is None:
        show_login()
    else:
        # Afficher l'interface correspondant au rôle
        if st.session_state.role == "Étudiant":
            show_student_interface()
        elif st.session_state.role == "Professeur":
            show_professor_interface()
        else:
            # Pour les autres rôles (Vice-Doyen, Admin, Chef Dept)
            st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
            st.sidebar.markdown(f"**Rôle:** {st.session_state.role}")
            
            if st.sidebar.button("🚪 Déconnexion"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            st.markdown('<div class="main-header">🎓 Plateforme Num_Exam</div>', unsafe_allow_html=True)
            st.markdown("### Bienvenue sur la plateforme de gestion des emplois du temps d'examens")
            
            st.info("👈 Utilisez le menu latéral pour accéder aux différentes fonctionnalités")
            
            # Afficher quelques statistiques globales (selon le rôle)
            try:
                kpis = db.get_global_kpis()
                
                st.markdown("### 📊 Vue d'ensemble")
                
                # Totaux globaux
                total_examens = kpis['nb_examens_planifies'].sum()
                total_etudiants = kpis['nb_etudiants'].sum()
                total_conflits = kpis['nb_conflits_non_resolus'].sum()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📝 Examens planifiés", f"{total_examens:,}")
                with col2:
                    st.metric("👨‍🎓 Étudiants", f"{total_etudiants:,}")
                with col3:
                    color = "normal" if total_conflits == 0 else "inverse"
                    st.metric("⚠️ Conflits non résolus", f"{total_conflits}", delta_color=color)
                
                # Tableau par département
                st.markdown("### 🏛️ Par département")
                st.dataframe(kpis, use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.warning(f"Impossible de charger les statistiques: {e}")

if __name__ == "__main__":
    main()