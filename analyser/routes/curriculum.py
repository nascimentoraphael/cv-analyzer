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
        self.job = {}  # Certifique-se de setar o job selecionado antes de processar
        self._ai = LlamaClient()
        self._file_service = FileService()
    
    def get_files(self, uploaded_files):
        saved_file_paths = self._file_service.save_uploaded_files(uploaded_files, 'storage')
        contents = self._file_service.read_all(saved_file_paths)
        return list(zip(contents, saved_file_paths))
   
    def process_single_cv(self, content, path, job):
        try:
            resum_result = self._ai.resume_cv(content)
            opnion = self._ai.generate_opnion(content, job)
            score = self._ai.generate_score(content, job)
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
            return None

    # Corrigindo o método de análise: agora ele faz parte da classe
    def create_analyse(self, uploaded_files, job_name):
        if 'processed' not in st.session_state:
            st.session_state.processed = False
        
        if not st.session_state.processed:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                files_to_process = self.get_files(uploaded_files)
                total_files = len(files_to_process)
                analysis_results = []
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [
                        executor.submit(self.process_single_cv, content, path, self.job)
                        for content, path in files_to_process
                    ]
                    
                    start_time = time.time()
                    for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                        if time.time() - start_time > MAX_PROCESSING_TIME:
                            st.error("Tempo máximo de processamento excedido!")
                            break
                        progress_text.text(f"Processando curriculum {i} de {total_files}")
                        progress_bar.progress(i / total_files)
                        result = future.result()
                        if result:
                            analysis_results.append(result)
                
                progress_text.empty()
                progress_bar.empty()
                
                if not analysis_results:
                    st.warning("Nenhum currículo processado com sucesso.")
                    return
                
                for result in analysis_results:
                    st.subheader(f"📌 Análise do Currículo para a vaga: **{job_name}**")
                    st.write("### **Resumo da IA:**", result['resum_result'])
                    st.write("### **Opinião da IA:**", result['opnion'])
                    st.write("## **📊 Pontuação Final**")
                    st.write(f"✅ **Relevantidade para a Vaga:** `{result['score_competence'][0]:.1f}`")
                    st.write(f"🔧 **Conhecimento em IoT e IIoT:** `{result['score_strategies'][0]:.1f}`")
                    st.write(f"🏭 **Experiência com Sistemas Industriais:** `{result['score_qualifications'][0]:.1f}`")
                    st.write(f"📈 **Gerenciamento de Projetos:** `{result['score']:.1f}`")
                    st.progress(int(result['score'] * 10))
                    st.divider()
                    
                st.session_state.processed = True  # Marca que o processamento foi concluído
            except Exception as e:
                st.error(f"Erro geral no processamento: {str(e)}")
                traceback.print_exc()
            finally:
                progress_text.empty()
                progress_bar.empty()
        else:
            st.info("Currículos já processados. Pressione 'R' para reiniciar o envio, se necessário.")

def create_analyse(self, uploaded_files, job_name):
    if 'processed' not in st.session_state:
        st.session_state.processed = False
        
    if not st.session_state.processed:
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        try:
            files_to_process = self.get_files(uploaded_files)
            total_files = len(files_to_process)
            analysis_results = []
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self.process_single_cv, content, path, self.job)
                    for content, path in files_to_process
                ]
                
                start_time = time.time()
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    if time.time() - start_time > MAX_PROCESSING_TIME:
                        st.error("Tempo máximo de processamento excedido!")
                        break
                    progress_text.text(f"Processando curriculum {i} de {total_files}")
                    progress_bar.progress(i / total_files)
                    result = future.result()
                    if result:
                        analysis_results.append(result)
            
            progress_text.empty()
            progress_bar.empty()
            
            if not analysis_results:
                st.warning("Nenhum currículo processado com sucesso.")
                return
            
            # INSERÇÃO DOS REGISTROS NO BANCO:
            for result in analysis_results:
                # Cria o registro do currículo (Resum)
                resum = ResumFactory(
                    job_id=self.job.get('id'),
                    content=result['resum_result'],
                    file=result['path'],
                    opnion=result['opnion'],
                    competence=result['score_competence'],
                    strategies=result['score_strategies'],
                    qualifications=result['score_qualifications'],
                ).create()
                
                # Cria o registro da análise (Analysis)
                AnalysisFactory(
                    resum_content=result['resum_result'],
                    job_id=self.job.get('id'),
                    resum_id=resum.id,
                    score=result['score']
                ).create()
                
                # Exibe os resultados (opcional)
                st.subheader(f"📌 Análise do Currículo para a vaga: **{job_name}**")
                st.write("### **Resumo da IA:**", result['resum_result'])
                st.write("### **Opinião da IA:**", result['opnion'])
                st.write("## **📊 Pontuação Final**")
                st.write(f"✅ **Relevantidade para a Vaga:** `{result['score_competence'][0]:.1f}`")
                st.write(f"🔧 **Conhecimento em IoT e IIoT:** `{result['score_strategies'][0]:.1f}`")
                st.write(f"🏭 **Experiência com Sistemas Industriais:** `{result['score_qualifications'][0]:.1f}`")
                st.write(f"📈 **Gerenciamento de Projetos:** `{result['score']:.1f}`")
                st.progress(int(result['score'] * 10))
                st.divider()
                
            st.session_state.processed = True
        except Exception as e:
            st.error(f"Erro geral no processamento: {str(e)}")
            traceback.print_exc()
        finally:
            progress_text.empty()
            progress_bar.empty()
    else:
        st.info("Currículos já processados. Pressione 'R' para reiniciar o envio, se necessário.")

    # Adicionar st.session_state para evitar reprocessamento:
def render_analysis(self, uploaded_files, job_name):
    if 'processed' not in st.session_state:  # Novo estado
        st.session_state.processed = False
        
    if not st.session_state.processed:
        # ... (código existente)
        
        # Ao final do processamento:
        st.session_state.processed = True
        st.experimental_rerun()  # Força atualização
        
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