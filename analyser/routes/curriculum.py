import uuid
from database.tiny_db import AnalyserDatabase
from service.llama_client import LlamaClient
from service.file_service import FileService
from factories.resume_factory import ResumFactory
from factories.analysis_factory import AnalysisFactory
import streamlit as st

DESTINATION_PATH = 'storage'

class CurriculumRoute:
    def __init__(self) -> None:
        self.database = AnalyserDatabase()
        self.jobs = [job.get('name') for job in self.database.jobs.all()]
        self.job = {}
        self._ai = LlamaClient()
        self._file_service = FileService()
        
    def resum(self, contents, job):
        results = []
        for cv, path in contents:
            result = self._ai.resume_cv(cv)
            results.append((result, path))
        return results
    
    def get_files(self, uploaded_files):
        saved_file_paths = self._file_service.save_uploaded_files(uploaded_files, 'storage')
        contents = self._file_service.read_all(saved_file_paths)
        return list(zip(contents, saved_file_paths))
   
    def create_analyse(self, uploaded_files, job_name):
        """Processa a análise dos currículos e retorna resultados para exibição no Streamlit"""
        try:
            # Configurar o job
            self.job = self.database.get_job_by_name(job_name)
            
            # Inicializar lista para armazenar resultados
            analysis_results = []
            
            # Processar cada arquivo
            for content, path in self.get_files(uploaded_files):
                # Gerar resumo do currículo
                resum_result = self._ai.resume_cv(content)
                
                # Gerar opinião sobre o currículo
                opnion = self._ai.generate_opnion(content, self.job)
                
                # Calcular pontuação
                score = self._ai.generate_score(content, self.job)
                
                # Calcular scores para diferentes categorias
                score_competence = self._ai.score_qualifications(content, self.job.get('competence'))
                score_strategies = self._ai.score_qualifications(content, self.job.get('strategies'))
                score_qualifications = self._ai.score_qualifications(content, self.job.get('qualifications'))
                
                # Armazenar resultados
                analysis_results.append({
                    'resum_result': resum_result,
                    'opnion': opnion,
                    'score': score,
                    'score_competence': score_competence,
                    'score_strategies': score_strategies,
                    'score_qualifications': score_qualifications,
                    'path': path
                })
            
            return analysis_results
        
        except Exception as e:
            st.error(f"Erro ao processar currículos: {str(e)}")
            return []

    def render_analysis(self, uploaded_files, job_name):
        """Método para renderizar a análise no Streamlit"""
        # Processar currículos
        analysis_results = self.create_analyse(uploaded_files, job_name)
        
        # Renderizar resultados
        for result in analysis_results:
            st.subheader(f"📌 Análise do Currículo para a vaga: **{job_name}**")
            
            # Resumo da IA
            st.write("### **Resumo da IA:**", result['resum_result'])
            
            # Opinião da IA
            st.write("### **Opinião da IA:**", result['opnion'])
            
            # Exibir Pontuação Final
            st.write("## **📊 Pontuação Final**")
            st.write(f"✅ **Relevantidade para a Vaga:** `{result['score_competence'][0]:.1f}`")
            st.write(f"🔧 **Conhecimento em IoT e IIoT:** `{result['score_strategies'][0]:.1f}`")
            st.write(f"🏭 **Experiência com Sistemas Industriais:** `{result['score_qualifications'][0]:.1f}`")
            st.write(f"📈 **Gerenciamento de Projetos:** `{result['score']:.1f}`")
            
            # Barra de progresso
            st.progress(int(result['score'] * 10))  # Normalizando para 0-100
            
            st.divider()  # Separador entre análises