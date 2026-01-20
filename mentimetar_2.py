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

MENTIMETER_LINK = "https://www.menti.com/aljtc951try4"

WRONG_ANSWER_INDICATORS = [
    "[class*='wrong']",
    "[class*='incorrect']",
    "[class*='error']",
    "[data-testid*='incorrect']",
    "[aria-label*='Incorrect']",
    "[aria-label*='incorrect']",
    ".m-e",
]

def generate_bot_name(bot_id):
    """Generira jedinstveno ime za bota"""
    random_suffix = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    return f"Bot_{bot_id}_{random_suffix}"

def enter_name_and_join(driver, bot_id):
    """Unosi ime i pridružuje se kvizu"""
    try:
        bot_name = generate_bot_name(bot_id)
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "input"))
        )
        
        inputs = driver.find_elements(By.TAG_NAME, "input")
        name_input = None
        
        for inp in inputs:
            if inp.is_displayed() and inp.get_attribute("type") in [None, "text"]:
                name_input = inp
                break
        
        if not name_input:
            raise Exception("Ne mogu pronaći polje za unos imena")
        
        name_input.clear()
        name_input.send_keys(bot_name)
        print(f"📝 Bot {bot_id:03d} unio ime: {bot_name}")
        
        time.sleep(0.5)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        join_button = None
        
        for btn in buttons:
            btn_text = btn.text.lower()
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            
            if any(x in btn_text or x in aria_label for x in ['join', 'submit', 'continue', 'start', 'enter']):
                if btn.is_displayed() and btn.is_enabled():
                    join_button = btn
                    break
        
        if not join_button:
            print(f"❌ Bot {bot_id:03d} ne može pronaći gumb za pridruživanje")
            return False
        
        join_button.click()
        print(f"✅ Bot {bot_id:03d} se pridružio kvizu")
        
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"❌ Bot {bot_id:03d} greška pri unosu imena: {e}")
        return False

def find_answer_button(driver, option_label, answer, bot_id, question_num):
    """Pronalazi i vraća gumb za odgovor sa beskonačnim čekanjem"""
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            print(f"⏳ Bot {bot_id:03d} -> Pitanje {question_num+1}: Pokušaj {attempt} - čeka gumb...")
            time.sleep(1)
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        # Kombinirana pretraga sa svim strategijama
        for btn in buttons:
            if not (btn.is_displayed() and btn.is_enabled()):
                continue
            
            btn_text = btn.text.strip()
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            btn_class = (btn.get_attribute("class") or "").lower()
            
            # Provjera: tekst, aria-label, klasa ili redoslijed
            if (option_label == btn_text or 
                option_label.lower() == btn_text.lower() or
                option_label.lower() in aria_label or
                (("option" in btn_class or "choice" in btn_class) and 
                 (option_label.lower() in btn_text.lower() or answer.upper() in btn_text))):
                return btn
        
        # Ako nije pronađeno, pokušaj sa redoslijedom
        option_buttons = [btn for btn in buttons 
                         if "option" in btn.text.strip().lower() 
                         and btn.is_displayed() and btn.is_enabled()]
        
        option_index = ord(answer.lower()) - ord('a')
        if 0 <= option_index < len(option_buttons):
            return option_buttons[option_index]

def check_wrong_answer(driver, bot_id, question_num):
    """Provjerava je li odgovor pogrešan"""
    
    # Provjera CSS selektora
    for selector in WRONG_ANSWER_INDICATORS:
        try:
            if any(e.is_displayed() for e in driver.find_elements(By.CSS_SELECTOR, selector)):
                return True
        except:
            pass
    
    # Provjera aria-label i teksta
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            if "incorrect" in aria_label or "wrong" in aria_label:
                return True
        
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "incorrect" in page_text or "wrong answer" in page_text or "wrong" in page_text:
            return True
    except:
        pass
    
    return False

def bot_worker(bot_id, answers, lock, stats):
    """Pokreće jednog bota koji odgovara na sva pitanja"""
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
        
        if not enter_name_and_join(driver, bot_id):
            raise Exception("Nije mogao ući u kviz")
        
        option_map = {'a': 'Option 1', 'b': 'Option 2', 'c': 'Option 3'}
        
        for question_num, answer in enumerate(answers):
            # Čekaj da se pojavi gumb za odgovor
            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "button"))
                    )
                    break
                except:
                    print(f"⏳ Bot {bot_id:03d} -> Pitanje {question_num+1}: Čeka gumb...")
                    time.sleep(1)
            
            option_label = option_map.get(answer.lower())
            if not option_label:
                raise Exception(f"Nepoznat odgovor: {answer}")
            
            answer_button = find_answer_button(driver, option_label, answer, bot_id, question_num)
            
            if not answer_button:
                raise Exception(f"Ne mogu pronaći odgovor {option_label}")
            
            answer_button.click()
            print(f"✅ Bot {bot_id:03d} -> Pitanje {question_num+1}: {answer.upper()}")
            
            time.sleep(2)
            
            if check_wrong_answer(driver, bot_id, question_num):
                print(f"💀 Bot {bot_id:03d} -> POGREŠAN ODGOVOR na pitanju {question_num+1}")
                raise Exception(f"Pogrešan odgovor na pitanju {question_num+1}")
            
            time.sleep(0.5)
        
        print(f"🎉 Bot {bot_id:03d} ZAVRŠIO SVIH 5 PITANJA! ✓✓✓✓✓")
        with lock:
            stats['completed'] += 1
            stats['correct'] += 1
        
    except Exception as e:
        with lock:
            stats['failed'] += 1
        print(f"❌ Bot {bot_id:03d} neuspješan: {str(e)[:50]}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    print("=" * 80)
    print(f"🚀 POKREĆEM MENTIMETAR BOT - 5 PITANJA × 3 OPCIJE = {3**5} KOMBINACIJE")
    print("=" * 80)
    
    all_combinations = list(product(['a', 'b', 'c'], repeat=5))
    
    def is_valid_combination(combo):
        """Provjerava ako kombinacija ima sve tri slova i nema uzastopnih ponavljanja"""
        combo_str = ''.join(combo)
        return (set(combo_str) == {'a', 'b', 'c'} and 
                all(combo_str[i] != combo_str[i+1] for i in range(len(combo_str) - 1)))
    
    all_combinations = [c for c in all_combinations if is_valid_combination(c)]
    print(f"📊 Ukupno kombinacija (nakon filtriranja): {len(all_combinations)}\n")
    
    stats = {'completed': 0, 'failed': 0, 'correct': 0}
    lock = threading.Lock()
    threads = []
    
    start_time = time.time()
    for bot_id, combination in enumerate(all_combinations):
        thread = threading.Thread(
            target=bot_worker, 
            args=(bot_id + 1, combination, lock, stats)
        )
        thread.start()
        threads.append(thread)
        
        time.sleep(0.15)
        
        if (bot_id + 1) % 10 == 0:
            with lock:
                total = stats['completed'] + stats['failed']
                percentage = (total / len(all_combinations)) * 100
                print(f"📍 Pokrenuto {bot_id + 1}/{len(all_combinations)} ({percentage:.1f}%)")
    
    print(f"\n⏳ Čekam da se svi botovi završe...\n")
    
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
    
    for thread in threads:
        thread.join()
    
    elapsed_time = time.time() - start_time
    
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
