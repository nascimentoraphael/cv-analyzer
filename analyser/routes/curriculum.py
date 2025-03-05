import uuid
from database.tiny_db import AnalyserDatabase
from service.llama_client import LlamaClient
from service.file_service import FileService
from factories.resume_factory import ResumFactory
from factories.analysis_factory import AnalysisFactory
import streamlit as st
import time
import concurrent.futures
import traceback

DESTINATION_PATH = 'storage'
MAX_PROCESSING_TIME = 300  # 5 minutos de timeout

class CurriculumRoute:
    def __init__(self) -> None:
        self.database = AnalyserDatabase()
        self.jobs = [job.get('name') for job in self.database.jobs.all()]
        self.job = {}
        self._ai = LlamaClient()
        self._file_service = FileService()
    
    def get_files(self, uploaded_files):
        saved_file_paths = self._file_service.save_uploaded_files(uploaded_files, 'storage')
        contents = self._file_service.read_all(saved_file_paths)
        return list(zip(contents, saved_file_paths))
   
    def process_single_cv(self, content, path, job):
        """Processa um único currículo"""
        try:
            # Gerar resumo do currículo
            resum_result = self._ai.resume_cv(content)
            
            # Gerar opinião sobre o currículo
            opnion = self._ai.generate_opnion(content, job)
            
            # Calcular pontuação
            score = self._ai.generate_score(content, job)
            
            # Calcular scores para diferentes categorias
            score_competence = self._ai.score_qualifications(content, job.get('competence'))
            score_strategies = self._ai.score_qualifications(content, job.get('strategies'))
            score_qualifications = self._ai.score_qualifications(content, job.get('qualifications'))
            
            return {
                'resum_result': resum_result,
                'opnion': opnion,
                'score': score,
                'score_competence': score_competence,
                'score_strategies': score_strategies,
                'score_qualifications': score_qualifications,
                'path': path
            }
        except Exception as e:
            st.error(f"Erro ao processar currículo {path}: {str(e)}")
            traceback.print_exc()
            return None

    def render_analysis(self, uploaded_files, job_name):
        """Renderiza a análise dos currículos com timeout e controle de estado"""
        # Configurar o job
        self.job = self.database.get_job_by_name(job_name)
        
        # Placeholder para mostrar progresso
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # Obter arquivos
            files_to_process = self.get_files(uploaded_files)
            total_files = len(files_to_process)
            
            # Lista para armazenar resultados
            analysis_results = []
            
            # Processamento paralelo com timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Preparar futures
                futures = [
                    executor.submit(self.process_single_cv, content, path, self.job) 
                    for content, path in files_to_process
                ]
                
                # Aguardar resultados com timeout
                start_time = time.time()
                completed_count = 0
                
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    # Verificar timeout
                    if time.time() - start_time > MAX_PROCESSING_TIME:
                        st.error("Tempo máximo de processamento excedido!")
                        break
                    
                    # Atualizar progresso
                    completed_count = i
                    progress_text.text(f"Processando curriculum {completed_count} de {total_files}")
                    progress_bar.progress(completed_count / total_files)
                    
                    # Obter resultado
                    result = future.result()
                    if result:
                        analysis_results.append(result)
            
            # Limpar indicadores de progresso
            progress_text.empty()
            progress_bar.empty()
            
            # Renderizar resultados
            if not analysis_results:
                st.warning("Nenhum currículo processado com sucesso.")
                return
            
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
        
        except Exception as e:
            st.error(f"Erro geral no processamento: {str(e)}")
            traceback.print_exc()
        finally:
            # Garantir que os indicadores de progresso sejam removidos
            progress_text.empty()
            progress_bar.empty()