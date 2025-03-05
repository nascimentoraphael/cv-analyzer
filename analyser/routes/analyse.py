import os
import pandas as pd
import streamlit as st
from database.tiny_db import AnalyserDatabase
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

class AnalyseRoute:
    def __init__(self) -> None:
        self.database = AnalyserDatabase()
        self.jobs = [job.get('name') for job in self.database.jobs.all()]
        self.job = {}
        self.data_analysis = {}
        self.resums = {}

    def _set_job_by_name(self, job_name):
        self.job = self.database.get_job_by_name(job_name)

    def _set_resums(self):
        self.resums = self.database.get_resums_by_job_id(self.job.get('id'))

    def _get_all_analysis(self):
        self.data_analysis = self.database.get_analysis_by_job_id(self.job.get('id'))
        return self.data_analysis
    
    def get_resum_by_resum_id(self, resum_id):
        return self.database.get_resum_by_resum_id(resum_id)
    
    def get_categories_job(self):
        return (
            self.job.get('competence'), 
            self.job.get('strategies'), 
            self.job.get('qualifications'),
        )

    def _create_selected_candidates_df(self, selected_candidates):
        return pd.DataFrame(selected_candidates)
    
    def get_resum_by_id(self, resum_id):
        return self.database.get_resum_by_id(resum_id)

    def _create_dataframe_to_analyse(self):
        self.df_candidate = pd.DataFrame(
            self._get_all_analysis(),
            columns=[
                'name',
                'education',
                'skills',
                'languages',
                'score',
                'resum_id',
                'id'
            ]
        )

        self.df_candidate.rename(
            columns={
                'name': 'Nome',
                'education': 'Educação',
                'skills': 'Habilidades',
                'languages': 'Idiomas',
                'score': 'score',
                'resum_id': 'resum_id',
                'id': 'id'
            }, inplace=True
        )

        if self.df_candidate.empty:
            print("⚠️ O DataFrame `df_candidate` está vazio.")

        return self.df_candidate

    def _grid_builder(self, df):
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=800)
        if not df.empty:
            gb.configure_column("score", header_name="score", sort="desc")
            gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        return gb.build()

    def render_grid(self, job_name):
        self._set_job_by_name(job_name)
        df = self._create_dataframe_to_analyse()
        
        if df.empty:
            st.warning("Nenhum candidato encontrado para esta vaga.")
            return pd.DataFrame()

        grid_options = self._grid_builder(df)
        response = AgGrid(
            df,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='balham',
        )
        
        selected_df = self._create_selected_candidates_df(response.get('selected_rows', []))
        return selected_df

    def _delete_all_files_into_analyse(self):
        for resum in self.resums:
            path = resum.get('file')
            if os.path.isfile(path):
                os.remove(path)

    def clean_analyse(self):
        self._set_resums()
        self.database.delete_all_resums_by_job_id(self.job.get('id'))
        self.database.delete_all_analysis_by_job_id(self.job.get('id'))
        self.database.delete_all_files_by_job_id(self.job.get('id'))
        self._delete_all_files_into_analyse()