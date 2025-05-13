from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import os
import traceback

def main():
    # Inicializa a lista de lojas com erro
    lojas_com_erro = []
    driver = None
    
    try:
        # Configurações do navegador
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 30)
        
        # Acessa a tela de login
        driver.get("https://dinamica.aktgestorpdv.com.br/login")
        print("🔐 Acessando página de login...")

        # --- LOGIN ---
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_input.send_keys("seu_login")

        senha_input = driver.find_element(By.NAME, "password")
        senha_input.send_keys("sua_senha")

        botao_entrar = driver.find_element(By.CLASS_NAME, "button")
        botao_entrar.click()
        print("✅ Login realizado com sucesso.")
        time.sleep(5)

        # --- FECHA A MODAL (se existir) ---
        try:
            botao_modal = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'NÃO QUERO VISUALIZAR OS DADOS')]"))
            )
            driver.execute_script("arguments[0].click();", botao_modal)
            print("✅ Modal fechada com sucesso.")
            time.sleep(2)
        except Exception:
            print("ℹ️ Modal não encontrada ou já fechada.")
            
        # --- NAVEGAÇÃO PARA A PÁGINA DE VISITAS ---
        print("⏳ Navegando para a página de visitas...")
        driver.get("https://dinamica.aktgestorpdv.com.br/trade/visits-panel")
        time.sleep(5)
        
        if "visits-panel" not in driver.current_url:
            print("⚠️ Redirecionamento não ocorreu como esperado. Tentando novamente...")
            driver.get("https://dinamica.aktgestorpdv.com.br/trade/visits-panel")
            time.sleep(8)
            
        print("✅ Navegação concluída.")
        
        # --- APLICAÇÃO DE FILTROS ---
        print("🔍 Aplicando filtros...")
        time.sleep(3)
        
        # Define a data via JavaScript
        try:
            date_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "date"))
            )
            driver.execute_script("arguments[0].setAttribute('value', '2025-04-16')", date_input)
            print("📅 Data definida: 2025-04-16")
            
            # Clica em algum lugar da página para confirmar a data
            driver.execute_script("document.body.click();")
            time.sleep(2)
        except Exception as date_error:
            print(f"⚠️ Erro ao definir data: {str(date_error)}")
        
        # Tenta selecionar a região
        try:
            # Tenta diferentes seletores para o dropdown de região
            selectors = [
                ".select2-selection--single", 
                "#select2-region-container",
                "span.select2-selection"
            ]
            
            region_dropdown = None
            for selector in selectors:
                try:
                    region_dropdown = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    region_dropdown.click()
                    print(f"✅ Dropdown de região encontrado e clicado")
                    break
                except Exception:
                    continue
            
            if region_dropdown:
                region_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "select2-search__field"))
                )
                region_input.send_keys("SP - Interior (Área V)")
                time.sleep(2)
                region_input.send_keys(Keys.ENTER)
                print("✅ Região 'SP - Interior (Área V)' selecionada.")
                time.sleep(3)
        except Exception:
            print("⚠️ Erro ao selecionar região")
        
        # --- COLETA DE DADOS - ABORDAGEM AMPLA PARA LOJAS COM ERRO ---
        MAX_PAGINAS = 228                                                                              # Limitando a 5 páginas
        pagina = 1
        
        print(f"\n📊 INICIANDO COLETA DE LOJAS COM ERRO (máximo {MAX_PAGINAS} páginas)")
        
        while pagina <= MAX_PAGINAS:
            print(f"\n==== PÁGINA {pagina}/{MAX_PAGINAS} ====")
            
            # Aguarda carregamento completo da página
            time.sleep(5)
            
            # Usa JavaScript para encontrar lojas com erro de forma mais abrangente
            lojas_erro_pagina = driver.execute_script("""
                const lojas_com_erro = [];
                
                // Função para verificar se um elemento está realmente visível
                function isElementVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           el.offsetParent !== null;
                }

                // Encontra todas as linhas da tabela
                const linhas = document.querySelectorAll('tr');
                
                linhas.forEach(linha => {
                    // Busca por diferentes indicadores de erro
                    const indicadoresErro = [
                        linha.querySelector('i.fas.fa-exclamation-triangle.text-danger'),
                        linha.querySelector('i.fa-exclamation-triangle'),
                        linha.querySelector('.text-danger'),
                        linha.querySelector('.erro'),
                        linha.querySelector('.warning')
                    ];
                    
                    // Verifica se algum indicador de erro está visível
                    const temErro = indicadoresErro.some(indicador => 
                        isElementVisible(indicador)
                    );
                    
                    if (temErro) {
                        // Tenta encontrar o nome da loja de diferentes formas
                        const colunas = linha.querySelectorAll('td');
                        
                        // Primeiro, tenta o span com detalhes pequenos
                        const spanDetalhes = linha.querySelector('span.d-block.text-muted.small');
                        if (spanDetalhes) {
                            const nomeLoja = spanDetalhes.textContent.trim();
                            if (nomeLoja && !lojas_com_erro.includes(nomeLoja)) {
                                lojas_com_erro.push(nomeLoja);
                            }
                        }
                        
                        // Se não encontrou, tenta a segunda coluna
                        if (colunas.length >= 2 && lojas_com_erro.length === 0) {
                            // Primeiro tenta o span
                            const spanNomeLoja = colunas[1].querySelector('span.d-block.text-muted.small');
                            const nomeLoja = spanNomeLoja 
                                ? spanNomeLoja.textContent.trim() 
                                : colunas[1].textContent.trim();
                            
                            if (nomeLoja && !lojas_com_erro.includes(nomeLoja)) {
                                lojas_com_erro.push(nomeLoja);
                            }
                        }
                    }
                });
                
                return lojas_com_erro;
            """)
            
            # Adiciona as lojas encontradas na página à lista geral
            for loja in lojas_erro_pagina:
                if loja and loja not in lojas_com_erro:
                    lojas_com_erro.append(loja)
                    print(f"❌ Loja com erro visível: {loja}")
            
            print(f"Encontradas {len(lojas_erro_pagina)} lojas com erro na página {pagina}")
            
            # Se chegou ao limite de páginas, encerra
            if pagina == MAX_PAGINAS:
                break
                
            # Tenta passar para a próxima página
            try:
                # Usar JavaScript para clicar no botão de próxima página
                proximo_disponivel = driver.execute_script("""
                    const botoes = Array.from(document.querySelectorAll('a, button'));
                    
                    // Procura por qualquer botão que possa ser 'próxima página'
                    const botaoProximo = botoes.find(b => 
                        (b.textContent.includes('Próximo') || 
                         b.textContent.includes('Próxima') ||
                         b.textContent.includes('Next') ||
                         b.querySelector('i.fa-chevron-right')) && 
                        !b.disabled && 
                        !b.classList.contains('disabled')
                    );
                    
                    if (botaoProximo) {
                        botaoProximo.click();
                        return true;
                    }
                    return false;
                """)
                
                if proximo_disponivel:
                    print("⏭️ Navegando para a próxima página...")
                    time.sleep(5)  # Aguarda carregamento
                    pagina += 1
                else:
                    print("ℹ️ Não há mais páginas disponíveis.")
                    break
            except Exception as e:
                print(f"⚠️ Erro ao navegar para próxima página: {str(e)}")
                break
        
        # --- RESUMO DA COLETA ---
        print(f"\n📊 RESULTADO FINAL: {len(lojas_com_erro)} lojas com erro encontradas")
        
        # Lista as lojas encontradas
        if lojas_com_erro:
            print("\n=== LISTA DE LOJAS COM ERRO ===")
            for i, loja in enumerate(lojas_com_erro, 1):
                print(f"{i}. {loja}")
            print("==============================\n")
        
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        traceback.print_exc()
    
    finally:
        # Fecha o navegador
        if driver:
            driver.quit()

        # Salva os dados, se houver
        if lojas_com_erro:
            df = pd.DataFrame(lojas_com_erro, columns=["Lojas com endereço errado"])
            df.to_excel("lojas_com_erro.xlsx", index=False)
            print(f"✅ Finalizado. Arquivo 'lojas_com_erro.xlsx' criado com {len(lojas_com_erro)} lojas.")
        else:
            print("⚠️ Nenhuma loja com erro encontrada. Planilha não foi gerada.")

# Executa o programa principal
if __name__ == "__main__":
    main()