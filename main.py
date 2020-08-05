from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from time import sleep
from timeit import default_timer
from bs4 import BeautifulSoup
from random import randint
from datetime import datetime
from dotenv import load_dotenv
from os import getenv, path
from re import search
import logging
import pandas as pd


def authorization(user_login, user_password):
    browser.get("https://klavogonki.ru/")
    browser.find_element_by_xpath('//a[@class="login"]').click()
    login = browser.find_element_by_xpath('//input[@name="login"]')
    password = browser.find_element_by_xpath('//input[@name="pass"]')
    login.send_keys(user_login)
    password.send_keys(user_password)
    browser.find_element_by_xpath('//input[@type="submit"]').click()


def get_text(time_limit=5 * 60):
    time = default_timer()
    while True:
        soup = BeautifulSoup(browser.page_source, 'html.parser')
        temp = soup.find('span', attrs={'id': 'waiting_timeout'})
        if temp.text == '00 00':
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            enters = soup.find('div', attrs={'id': 'typetext'})
            text = ''
            for i in enters.contents[0].contents[1:3]:
                for j in i.contents:
                    try:
                        if len(j.attrs) == 0:
                            text += j.text
                    except Exception as error:
                        logger.exception(error)
                        text += j
            text = text.replace('c', 'с').replace('o', 'о')
            inp = browser.find_element_by_xpath('//Input[@name="sometext"]')
            logger.info(text)
            return text, inp
        if default_timer() - time > time_limit:
            return None


def send_key(inp, speed, key, start_time, key_num=0):
    inp.send_keys(key)
    time_now = default_timer() - start_time
    time = key_num * 60 / speed
    if time_now < time:
        sleep(time - time_now)


def write_text(text, inp, speed, mistake=0):
    key_num = 0
    start_time = default_timer()
    for i in text:
        key_num += 1
        seed = randint(0, 1000)
        if seed <= mistake:
            send_key(inp, speed, chr(ord(i) + 1), start_time)
            send_key(inp, speed, Keys.BACKSPACE, start_time)
        send_key(inp, speed, i, start_time, key_num)


def debug():
    last = ''
    while True:
        speed = int(input('speed: '))
        if '/g/' in browser.current_url and last != browser.current_url:
            last = browser.current_url
            text, inp = get_text()
            logger.info(f'speed = {speed}')
            sleep(0.1)
            write_text(text, inp, speed)


def save_result(mode, contest, point, ball, speed, res, text):
    time_check = default_timer()
    now = datetime.now()
    table = pd.read_excel('Results.xlsx', 'main')
    time = search(r'\d+:\d+\W\d', res)
    error = search(r'\d+ \w+ \D\d+\W\d+%\D', res)
    result = search(r'\d+ место', res)
    speed_real = search(r'\d{3} зн/мин', res)
    table.loc[table.shape[0]] = [now.strftime("%d-%m-%Y %H:%M"), mode, 'Да' if contest else 'Нет',
                                 point, ball, speed, speed_real, result, error, time, text]
    table.to_excel('Results.xlsx', 'main', index=False)
    logger.info(f'Сохранили результаты за {round(default_timer() - time_check, 4)}с.')


def start_game(contest, min_speed, max_speed, stop, mistake):
    if contest:
        browser.find_element_by_xpath('//*[@id="competition_btn_accept"]').click()
        time_limit = 70
    else:
        time_limit = 20
    text, inp = get_text(time_limit)
    if text is None:
        return
    speed = randint(min_speed, max_speed)
    logger.info(f'speed = {speed}')
    sleep(stop)
    write_text(text, inp, speed, mistake)
    sleep(0.5)
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    enters = soup.find('div', attrs={'class': 'player you ng-scope'}).text
    temp = soup.find('table', attrs={'class': 'scores-table'}).text.split('\n')
    return temp[3], temp[14], speed, enters, text


def qualification():
    last = ''
    while True:
        if '/g/' in browser.current_url and last != browser.current_url:
            last = browser.current_url
            input('start!')
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            temp = soup.find('div', attrs={'class': 'correct_errors_text errors_text'})
            text = temp.text.replace('c', 'с').replace('o', 'о')
            inp = browser.find_element_by_xpath('//*[@id="inputtext"]')
            inp.send_keys(Keys.CONTROL + "a")
            inp.send_keys(Keys.BACKSPACE)
            inp.send_keys(text)
            inp.send_keys(Keys.ENTER)


def start(mask, on_contest):
    const_link = 'https://klavogonki.ru'
    Time = default_timer()
    while True:
        logger.debug(browser.current_url)
        if browser.current_url != 'https://klavogonki.ru/gamelist/' or default_timer() - Time > 30:
            browser.get('https://klavogonki.ru/gamelist/')
            Time = default_timer()
        soup = BeautifulSoup(browser.page_source, 'html.parser')
        enters = soup.find_all('td', attrs={'class': 'enter'})
        modes = soup.find_all('td', attrs={'class': 'sign'})
        times = soup.find_all('td', attrs={'class': 'status'})
        players = soup.find_all('td', attrs={'class': 'players ng-scope'})
        check = False
        for link, mode, time, player in zip(enters, modes, times, players):
            check = True
            try:
                link = link.contents[1].contents[1].attrs['href']
                text = time.text
                try:
                    mode = mode.contents[1].attrs['title'] + ' ' + search(r'«.+»', text)
                except Exception as error:
                    logger.exception(error)
                    mode = mode.contents[1].attrs['title']
                contest = 'стоимость:  очков' not in text
                time = 60 * int(text[3:5]) + int(text[6:8])
                logger.info(f'Режим: {mode}, ссылка на игру {link}, соревнование? {"Да" if contest else "Нет"}, время {time}')
                if mode in mask and 5 <= time <= 60 and contest and on_contest:
                    logger.info('Поехали')
                    browser.get(f'{const_link}{link}')
                    point, ball, speed, res, text = start_game(contest, 530, 560, 0.05, 15)
                    save_result(mode, contest, point, ball, speed, res, text)
                    break
                if mode in mask and 3 <= time <= 10 and not contest:
                    logger.info('Поехали')
                    browser.get(f'{const_link}{link}')
                    point, ball, speed, res, text = start_game(contest, 500, 560, 0.07, 20)
                    save_result(mode, contest, point, ball, speed, res, text)
                    break
            except Exception as error:
                logger.exception(error)
        else:
            if check:
                try:
                    browser.find_element_by_xpath('//*[@id="create_game"]').click()
                    browser.find_element_by_xpath('//*[@id="timeout"]/option[1]').click()
                    browser.find_element_by_xpath('//*[@id="submit_btn"]').click()
                    sleep(0.5)
                    try:
                        browser.find_element_by_xpath('//*[@id="host_start"]').click()
                    except Exception as error:
                        logger.exception(error)
                    sleep(4)
                    point, ball, speed, res, text = start_game(False, 500, 560, 0.07, 20)
                    save_result('My game', False, point, ball, speed, res, text)
                except Exception as error:
                    logger.exception(error)
        sleep(2)


if __name__ == '__main__':
    '''Создаём лог'''
    logger = logging.getLogger('BOT')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter('%(filename)s[LINE:%(lineno)-3s]# %(levelname)-8s [%(asctime)s]  %(message)s'))
    logger.addHandler(file_handler)
    '''Запускаем браузер'''
    profile = Options()
    profile.add_argument("--start-maximized")
    browser = webdriver.Chrome(chrome_options=profile)
    '''Загружаем .env с логином и паролем'''
    dotenv_path = path.join(path.dirname(__file__), '.env')
    if path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        print('Напишите в файл .env ваш логин и пароль')
        with open('.env', 'w') as file:
            file.write('KLAVAGONKI_LOGIN = login\nKLAVAGONKI_PASSWORD = password')
    '''Пытаемся авторизоваться'''
    authorization(getenv('KLAVAGONKI_LOGIN'), getenv('KLAVAGONKI_PASSWORD'))
    '''Запускаем нужный режим'''
    # debug()  # - набирает текст с заданной скоростью, если зашёл в какой-то режим
    # qualification()  # - исправляет ошибки после квалификации
    start(['Обычный', 'По словарю «Лавка миров»'], True)
