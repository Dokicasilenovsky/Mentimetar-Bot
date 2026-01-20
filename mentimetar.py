import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from itertools import product
import random
import string
import subprocess
import os

#LINK
MENTIMETER_LINK = "https://www.menti.com/alnz7t7nj2de" 

#Selektri za unos imena
NAME_INPUT_SELECTORS = [
    "input[data-testid='quiz-player-name']",
    "input#quiz-name",
    "input[name='quiz-name']",
    "input[type='text']"
]

JOIN_BUTTON_SELECTORS = [
    "button[data-testid='quiz-player-form-submit']",
    "button[type='submit']",
    "button:contains('Join quiz')",
    "button:contains('Join')",
    "button:contains('Continue')"
]


ANSWER_SELECTORS = [
    "button[type='submit'][aria-label*='Option {option}']",
    "button[aria-label*='Option {option}']",
    "button[type='submit'][aria-label*='{option}']"
]

WRONG_ANSWER_INDICATORS = [
    "[class*='wrong']",
    "[class*='incorrect']",
    "[class*='error']",
    "[data-testid*='incorrect']",
    "[aria-label*='Incorrect']",
    "[aria-label*='incorrect']",
    ".m-e",  # Mentimeter koristi specifičnu klasu za greške
]

def generate_bot_name(bot_id):
    """Generira jedinstveno ime za bota"""
    letters = string.ascii_lowercase
    random_suffix = ''.join(random.choice(letters) for i in range(4))
    return f"Bot_{bot_id}_{random_suffix}"

def enter_name_and_join(driver, bot_id):
    """Unosi ime i pridružuje se kvizu"""
    try:
        # Generiraj jedinstveno ime
        bot_name = generate_bot_name(bot_id)
        
        # Čekaj da se polje za ime pojavi (novo: input je direktno bez data-testid)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "input"))
        )
        
        # Pronađi sve input polja i filtriraj
        inputs = driver.find_elements(By.TAG_NAME, "input")
        name_input = None
        
        # Pronađi prvi input koji je vidljiv (za unos imena)
        for inp in inputs:
            if inp.is_displayed() and inp.get_attribute("type") in [None, "text"]:
                name_input = inp
                break
        
        if not name_input:
            raise Exception("Ne mogu pronaći polje za unos imena")
        
        # Unesi ime
        name_input.clear()
        name_input.send_keys(bot_name)
        print(f"📝 Bot {bot_id:03d} unio ime: {bot_name}")
        
        # Čekaj malo prije nego što kliknemo gumb
        time.sleep(0.5)
        
        # Pronađi i klikni gumb za pridruživanje
        join_button = None
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        for btn in buttons:
            btn_text = btn.text.lower()
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            
            # Tražimo gumb koji sadrži 'join', 'continue', 'submit' ili 'start'
            if any(x in btn_text or x in aria_label for x in ['join', 'submit', 'continue', 'start', 'enter']):
                # Preskočimo gumb ako je 'hidden' ili 'disabled'
                if btn.is_displayed() and btn.is_enabled():
                    join_button = btn
                    break
        
        if not join_button:
            print(f"❌ Bot {bot_id:03d} ne može pronaći gumb za pridruživanje")
            return False
        
        join_button.click()
        print(f"✅ Bot {bot_id:03d} se pridružio kvizu")
        
        # Čekaj da se stranica učita nakon unosa imena
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"❌ Bot {bot_id:03d} greška pri unosu imena: {e}")
        return False

# 👇 SELEKTORI ZA ODGOVORE PREMA ARIA-LABEL
ANSWER_SELECTORS = [
    "button[type='submit'][aria-label*='{option}']",
    "button[aria-label*='{option}']"
]

def bot_worker(bot_id, answers, lock, stats):
    """
    Pokreće jednog bota koji odgovara na sva pitanja
    lock: zaključavanja za pisanje u stats
    stats: dictionary sa {'completed': count, 'failed': count, 'correct': count}
    """
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        driver.get(MENTIMETER_LINK)
        
        print(f"🤖 Bot {bot_id:03d} pokrenuo se | Odgovori: {''.join(answers)}")
        
        # KORAK 1: Unesi ime i pridruži se kvizu
        if not enter_name_and_join(driver, bot_id):
            raise Exception("Nije mogao ući u kviz")
        
        # KORAK 2: Odgovori na sva pitanja
        answers_given = 0
        for question_num, answer in enumerate(answers):
            # Čekaj da se pojavi gumb za odgovor - BESKONAČNO ČEKANJE
            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "button"))
                    )
                    break  # Gumb pronađen, izlazi iz while petlje
                except:
                    # Timeout, ali nastavi čekati
                    print(f"⏳ Bot {bot_id:03d} -> Pitanje {question_num+1}: Čeka gumb...")
                    time.sleep(1)
                    continue
            
            # Mapiraj a/b/c na Option 1/2/3
            option_map = {'a': 'Option 1', 'b': 'Option 2', 'c': 'Option 3'}
            option_label = option_map.get(answer.lower())
            
            if not option_label:
                raise Exception(f"Nepoznat odgovor: {answer}")
            
            # BESKONAČNA PETLJA - ČEKAJ GUMB KOLIKO GOD TREBALO
            answer_button = None
            attempt = 0
            while answer_button is None:
                attempt += 1
                if attempt > 1:
                    print(f"⏳ Bot {bot_id:03d} -> Pitanje {question_num+1}: Pokušaj {attempt} - čeka gumb...")
                    time.sleep(1)
                
                # STRATEGIJA 1: Traži direktno po tekstu gumba ("Option 1", "Option 2", "Option 3")
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    if option_label == btn_text or option_label.lower() == btn_text.lower():
                        if btn.is_displayed() and btn.is_enabled():
                            answer_button = btn
                            break
                
                # STRATEGIJA 2: Ako ne nađemo direktno, traži po aria-label atributu
                if not answer_button:
                    for btn in buttons:
                        aria_label = (btn.get_attribute("aria-label") or "").lower()
                        if option_label.lower() in aria_label and btn.is_displayed() and btn.is_enabled():
                            answer_button = btn
                            break
                
                # STRATEGIJA 3: Traži gumbove koji su u kontejneru za odgovore (obično imaju slične klase)
                if not answer_button:
                    for btn in buttons:
                        btn_class = (btn.get_attribute("class") or "").lower()
                        btn_text = btn.text.strip()
                        # Ako gumb sadrži "option" u klasi ili je vidljiv i ima tekst
                        if ("option" in btn_class or "choice" in btn_class) and btn.is_displayed():
                            if option_label.lower() in btn_text.lower() or answer.upper() in btn_text:
                                if btn.is_enabled():
                                    answer_button = btn
                                    break
                
                # STRATEGIJA 4: Ako sve ostalo ne radi, pronađi "Option X" po redoslijedu gumbova
                if not answer_button:
                    option_buttons = []
                    for btn in buttons:
                        btn_text = btn.text.strip()
                        if "option" in btn_text.lower() and btn.is_displayed() and btn.is_enabled():
                            option_buttons.append(btn)
                    
                    # Mapiraj a->0, b->1, c->2
                    option_index = ord(answer.lower()) - ord('a')
                    if 0 <= option_index < len(option_buttons):
                        answer_button = option_buttons[option_index]
            
            # Kad pronađe gumb, klikni ga
            answer_button.click()
            print(f"✅ Bot {bot_id:03d} -> Pitanje {question_num+1}: {answer.upper()}")
            answers_given += 1
            
            # Čekaj da se pojavi rezultat
            time.sleep(2)
            
            # Provjeri je li odgovor pogrešan
            wrong_detected = False
            
            # Metoda 1: CSS selektori za 'wrong' klasu
            for selector in WRONG_ANSWER_INDICATORS:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 0 and any(e.is_displayed() for e in elements):
                        wrong_detected = True
                        break
                except:
                    pass
            
            # Metoda 2: Provjeri aria-label za 'incorrect'
            if not wrong_detected:
                try:
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in all_buttons:
                        aria_label = btn.get_attribute("aria-label") or ""
                        if "incorrect" in aria_label.lower() or "wrong" in aria_label.lower():
                            wrong_detected = True
                            break
                except:
                    pass
            
            # Metoda 3: Provjeri tekstualni sadržaj
            if not wrong_detected:
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if "incorrect" in page_text or "wrong answer" in page_text or "wrong" in page_text:
                        wrong_detected = True
                except:
                    pass
            
            if wrong_detected:
                print(f"💀 Bot {bot_id:03d} -> POGREŠAN ODGOVOR na pitanju {question_num+1}")
                raise Exception(f"Pogrešan odgovor na pitanju {question_num+1}")
            
            time.sleep(0.5)
        
        # Sve je prošlo OK
        print(f"🎉 Bot {bot_id:03d} ZAVRŠIO SVIH 5 PITANJA! ✓✓✓✓✓")
        with lock:
            stats['completed'] += 1
            stats['correct'] += 1
        
    except Exception as e:
        with lock:
            stats['failed'] += 1
        print(f"❌ Bot {bot_id:03d} neuspješan: {str(e)[:50]}")
    finally:
        # Osiguraj da se driver zatvori čak i ako dođe do greške
        if driver:
            try:
                driver.quit()
            except:
                pass

# Test funkcija za provjeru selektora (opciono)
# Ako trebate testirati selektore prije pokretanja botova, odkomentarajte ove linije:
# def test_name_input():
#     """Testira selektore za unos imena"""
#     driver = webdriver.Chrome()
#     driver.get(MENTIMETER_LINK)
#     ...

def debug_html_elements():
    """Provjerava HTML strukture na Mentimeter stranici"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    driver.get(MENTIMETER_LINK)
    
    print("=" * 80)
    print("🔍 PROVJERA HTML ELEMENATA NA MENTIMETER STRANICI")
    print("=" * 80)
    
    time.sleep(3)
    
    # 1. Traži input polja za ime
    print("\n📝 INPUT POLJA ZA IME:")
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for i, inp in enumerate(inputs[:10]):
        if inp.is_displayed():
            attrs = {
                'type': inp.get_attribute('type'),
                'placeholder': inp.get_attribute('placeholder'),
                'id': inp.get_attribute('id'),
                'name': inp.get_attribute('name'),
                'value': inp.get_attribute('value'),
                'visible': inp.is_displayed(),
            }
            print(f"  Input {i} (VIDLJIV): {attrs}")
    
    # 2. Unos imena i prijava
    print("\n✍️  UNOS IMENA I PRIJAVA U KVIZ...")
    input_field = None
    for inp in inputs:
        if inp.is_displayed() and inp.get_attribute("type") in [None, "text"]:
            input_field = inp
            break
    
    if input_field:
        input_field.send_keys("DebugBot")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if btn.is_displayed() and any(x in btn.text.lower() for x in ['join', 'submit', 'continue']):
                btn.click()
                break
        time.sleep(2)
    
    # 3. Sada analiziraj sve gumbove nakon što se pojavi prvo pitanje
    print("\n🔘 SVE GUMBOVE NA STRANICI (samo vidljive):")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"\nUkupno gumbova na stranici: {len(buttons)}")
    
    option_buttons = []
    for i, btn in enumerate(buttons):
        if btn.is_displayed():
            attrs = {
                'text': btn.text[:50],
                'type': btn.get_attribute('type'),
                'aria-label': btn.get_attribute('aria-label'),
                'class': btn.get_attribute('class')[:80],
                'role': btn.get_attribute('role'),
                'enabled': btn.is_enabled(),
            }
            if 'option' in btn.text.lower():
                option_buttons.append((i, btn))
                print(f"  Button {i} (OPTION): {attrs}")
            elif i < 15:  # Prikaži prve gumbove
                print(f"  Button {i}: {attrs}")
    
    print(f"\n📋 PRONAĐENI GUMBOVI SA 'OPTION' U TEKSTU: {len(option_buttons)}")
    for idx, (i, btn) in enumerate(option_buttons):
        print(f"  [{idx}] Button {i}: '{btn.text.strip()}' - enabled={btn.is_enabled()}")
    
    # 4. Analiza klasa gumbova za odgovore
    print("\n🎯 ANALIZA KLASA GUMBOVA ZA ODGOVORE:")
    for idx, (i, btn) in enumerate(option_buttons[:5]):
        class_attr = btn.get_attribute('class') or ""
        print(f"  Odgovor {idx}: class='{class_attr}'")
    
    # 5. Traži elemente koji označavaju pogrešan odgovor
    print("\n❌ ELEMENTE ZA DETEKTOVANJE POGREŠNOG ODGOVORA:")
    for keyword in ['wrong', 'incorrect', 'error', 'invalid']:
        try:
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
            if elements:
                print(f"  Pronađeni elementi sa '{keyword}' u tekstu: {len(elements)}")
                for i, elem in enumerate(elements[:2]):
                    print(f"    - {elem.tag_name}: text='{elem.text[:40]}'")
        except:
            pass
    
    # Provjeri CSS selektore za greške
    print("\n📌 CSS SELEKTORI ZA GREŠKE:")
    for selector in WRONG_ANSWER_INDICATORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"  Pronađeni elementi sa '{selector}': {len(elements)}")
        except:
            pass
    
    print("\n" + "=" * 80)
    driver.quit()

# 👇 POKRENI SVE KOMBINACIJE (243 BOTA)

if __name__ == "__main__":
    import sys
    
    # Ako je prvi argument 'debug', pokreni debug funkciju
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
        print("\n🔧 POKRENUO SAM DEBUG MOD - PROVJERAVAMO HTML ELEMENTE...\n")
        debug_html_elements()
        sys.exit(0)
    
    print("=" * 80)
    print(f"🚀 POKREĆEM MENTIMETAR BOT - 5 PITANJA × 3 OPCIJE = {3**5} KOMBINACIJE")
    print("=" * 80)
    print("\n💡 Savjet: Ako trebate provjeriti HTML elemente, pokrenite:")
    print("   python mentimetar.py debug\n")
    
    all_combinations = list(product(['a','b','c'], repeat=5))
    
    # Filtriraj kombinacije - makni one sa ponavljanjem ili gdje nedostaje neko slovo
    def is_valid_combination(combo):
        """Provjerava ako kombinacija ima sve tri slova i nema uzastopnih ponavljanja"""
        combo_str = ''.join(combo)
        
        # Provjera 1: Moraju biti sva tri slova (a, b, c)
        if set(combo_str) != {'a', 'b', 'c'}:
            return False
        
        # Provjera 2: Nema 2 ili više uzastopnih istih znakova
        for i in range(len(combo_str) - 1):
            if combo_str[i] == combo_str[i+1]:
                return False
        
        return True
    
    all_combinations = [c for c in all_combinations if is_valid_combination(c)]
    print(f"📊 Ukupno kombinacija (nakon filtriranja): {len(all_combinations)}")
    print()
    
    # Brojač za ispis statistike
    stats = {'completed': 0, 'failed': 0, 'correct': 0}
    lock = threading.Lock()
    threads = []
    
    # Pokreni sve botove
    start_time = time.time()
    for bot_id, combination in enumerate(all_combinations):
        thread = threading.Thread(
            target=bot_worker, 
            args=(bot_id + 1, combination, lock, stats)
        )
        thread.start()
        threads.append(thread)
        
        # Delay između pokretanja botova da se ne preplitaju previše
        time.sleep(0.15)
        
        # Ispis napretka svaki 10. bot
        if (bot_id + 1) % 10 == 0:
            with lock:
                completed = stats['completed']
                failed = stats['failed']
                total = completed + failed
                percentage = (total / len(all_combinations)) * 100
                print(f"📍 Pokrenuto {bot_id + 1}/{len(all_combinations)} ({percentage:.1f}%) | "
                      f"✅ {completed}, ❌ {failed}")
    
    print(f"\n⏳ Čekam da se svi botovi završe... (ovo može potrajati nekoliko minuta)")
    
    # Čekaj da se svi thread-ovi završe sa ispisom napretka
    last_status = {'completed': 0, 'failed': 0}
    while any(t.is_alive() for t in threads):
        time.sleep(2)
        with lock:
            if stats['completed'] + stats['failed'] > last_status['completed'] + last_status['failed']:
                last_status['completed'] = stats['completed']
                last_status['failed'] = stats['failed']
                total = stats['completed'] + stats['failed']
                percentage = (total / len(all_combinations)) * 100
                print(f"⏳ Napredak: {total}/{len(all_combinations)} ({percentage:.1f}%) | ✅ {stats['completed']}, ❌ {stats['failed']}")
    
    # Osiguraj da su svi thread-ovi završeni
    for thread in threads:
        thread.join()
    
    elapsed_time = time.time() - start_time
    
    # Ispis finalne statistike
    print("\n" + "=" * 80)
    print("📊 FINALNA STATISTIKA")
    print("=" * 80)
    print(f"✅ Uspješno završenih: {stats['completed']}/{len(all_combinations)}")
    print(f"❌ Neuspješnih: {stats['failed']}/{len(all_combinations)}")
    total_completed = stats['completed'] + stats['failed']
    if total_completed > 0:
        success_rate = (stats['completed'] / total_completed) * 100
        print(f"📈 Stopa uspjeha: {success_rate:.1f}%")
    print(f"⏱️  Vrijeme trajanja: {elapsed_time:.1f} sekundi ({elapsed_time/60:.1f} minuta)")
    print("=" * 80)
    
    if stats['completed'] > 0:
        print(f"\n🎯 BRISANJE NEUSPJEŠNIH BOTOVA...")
        for i in range(1, 244):
            bot_dir = f"/Users/mihaelpurar/Desktop/MentimetarBot/bot_{i}"
            try:
                subprocess.run(["rm", "-rf", bot_dir], check=True)
                if i <= 10 or i % 50 == 0:
                    print(f"🗑️  Obrisan direktorij bot_{i}")
            except:
                pass
        print("✅ Čišćenje gotovo!")