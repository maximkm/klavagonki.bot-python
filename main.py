from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from time import sleep
from timeit import default_timer
from bs4 import BeautifulSoup
from random import randint
from datetime import datetime
import pandas as pd
import re

profile = Options()
profile.add_argument("--start-maximized")
klava = webdriver.Chrome(chrome_options=profile)


def authorization(user_login, user_password):
    klava.get("https://klavogonki.ru/")
    klava.find_element_by_xpath('//a[@class="login"]').click()
    login = klava.find_element_by_xpath('//input[@name="login"]')
    password = klava.find_element_by_xpath('//input[@name="pass"]')
    login.send_keys(user_login)
    password.send_keys(user_password)
    klava.find_element_by_xpath('//input[@type="submit"]').click()


def get_text(time_limit=5 * 60):
    time = default_timer()
    while True:
        soup = BeautifulSoup(klava.page_source, 'html.parser')
        temp = soup.find('span', attrs={'id': 'waiting_timeout'})
        if temp.text == '00 00':
            soup = BeautifulSoup(klava.page_source, 'html.parser')
            enters = soup.find('div', attrs={'id': 'typetext'})
            text = ''
            for i in enters.contents[0].contents[1:3]:
                for j in i.contents:
                    try:
                        if len(j.attrs) == 0:
                            text += j.text
                    except:
                        text += j
            text = text.replace('c', 'с').replace('o', 'о')
            inp = klava.find_element_by_xpath('//Input[@name="sometext"]')
            print(text)
            return text, inp
        if default_timer() - time > time_limit:
            return None


def send_key(inp, speed, key, start, key_num=0):
    inp.send_keys(key)
    time_now = default_timer() - start
    time = key_num * 60 / speed
    if time_now < time:
        sleep(time - time_now)


def write_text(text, inp, speed, mistake=0):
    key_num = 0
    start = default_timer()
    for i in text:
        key_num += 1
        seed = randint(0, 1000)
        if seed <= mistake:
            send_key(inp, speed, chr(ord(i) + 1), start)
            send_key(inp, speed, Keys.BACKSPACE, start)
        send_key(inp, speed, i, start, key_num)


def debug():
    last = ''
    while True:
        speed = int(input('speed: '))
        if '/g/' in klava.current_url and last != klava.current_url:
            last = klava.current_url
            text, inp = get_text()
            print(f'speed = {speed}')
            sleep(0.1)
            write_text(text, inp, speed)


time_parse = re.compile('\d+:\d+\W\d')
error_parse = re.compile('\d+ \w+ \D\d+\W\d+%\D')
result_parse = re.compile('\d+ место')
speed_parse = re.compile('\d{3} зн/мин')


def save_result(mode, contest, point, ball, speed, res, text):
    time_check = default_timer()
    now = datetime.now()
    table = pd.read_excel('Results.xlsx', 'main')
    time = re.findall(time_parse, res)[0]
    error = re.findall(error_parse, res)[0]
    result = re.findall(result_parse, res)[0]
    speed_real = re.findall(speed_parse, res)[0]
    table.loc[table.shape[0]] = [now.strftime("%d-%m-%Y %H:%M"), mode, 'Да' if contest else 'Нет',
                                 point, ball, speed, speed_real, result, error, time, text]
    table.to_excel('Results.xlsx', 'main', index=False)
    print(f'Сохранили результаты за {round(default_timer() - time_check, 4)}с.')


def start_game(contest, min_speed, max_speed, stop, mistake):
    if contest:
        klava.find_element_by_xpath('//*[@id="competition_btn_accept"]').click()
        time_limit = 70
    else:
        time_limit = 20

    text, inp = get_text(time_limit)
    if text is None:
        return
    speed = randint(min_speed, max_speed)
    print(f'speed = {speed}')
    sleep(stop)
    write_text(text, inp, speed, mistake)
    sleep(0.5)
    soup = BeautifulSoup(klava.page_source, 'html.parser')
    enters = soup.find('div', attrs={'class': 'player you ng-scope'}).text
    temp = soup.find('table', attrs={'class': 'scores-table'}).text.split('\n')
    return temp[3], temp[14], speed, enters, text


def qualification():
    last = ''
    while True:
        if '/g/' in klava.current_url and last != klava.current_url:
            last = klava.current_url
            input('start!')
            soup = BeautifulSoup(klava.page_source, 'html.parser')
            temp = soup.find('div', attrs={'class': 'correct_errors_text errors_text'})
            text = temp.text.replace('c', 'с').replace('o', 'о')
            inp = klava.find_element_by_xpath('//*[@id="inputtext"]')
            inp.send_keys(Keys.CONTROL + "a")
            inp.send_keys(Keys.BACKSPACE)
            inp.send_keys(text)
            inp.send_keys(Keys.ENTER)


def start(mask, on_contest):
    const_link = 'https://klavogonki.ru'
    game_name = re.compile('«.+»')
    Time = default_timer()

    while True:
        print(klava.current_url)
        if klava.current_url != 'https://klavogonki.ru/gamelist/' or default_timer() - Time > 30:
            klava.get('https://klavogonki.ru/gamelist/')
            Time = default_timer()
        soup = BeautifulSoup(klava.page_source, 'html.parser')
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
                    mode = mode.contents[1].attrs['title'] + ' ' + re.findall(game_name, text)[0]
                except Exception as error:
                    print(error)
                    mode = mode.contents[1].attrs['title']
                contest = 'стоимость:  очков' not in text
                time = 60 * int(text[3:5]) + int(text[6:8])
                print(f'Режим: {mode}, ссылка на игру {link}, соревнование? {"Да" if contest else "Нет"}, время {time}')
                if mode in mask and 5 <= time <= 60 and contest and on_contest:
                    print('Поехали')
                    klava.get(f'{const_link}{link}')
                    point, ball, speed, res, text = start_game(contest, 530, 560, 0.05, 15)
                    save_result(mode, contest, point, ball, speed, res, text)
                    break
                if mode in mask and 3 <= time <= 10 and not contest:
                    print('Поехали')
                    klava.get(f'{const_link}{link}')
                    point, ball, speed, res, text = start_game(contest, 500, 560, 0.07, 20)
                    save_result(mode, contest, point, ball, speed, res, text)
                    break
            except Exception as error:
                print(error)
        else:
            if check:
                try:
                    klava.find_element_by_xpath('//*[@id="create_game"]').click()
                    klava.find_element_by_xpath('//*[@id="timeout"]/option[1]').click()
                    klava.find_element_by_xpath('//*[@id="submit_btn"]').click()
                    sleep(0.5)
                    try:
                        klava.find_element_by_xpath('//*[@id="host_start"]').click()
                    except Exception as error:
                        print(error)
                    sleep(4)
                    point, ball, speed, res, text = start_game(False, 500, 560, 0.07, 20)
                    save_result('My game', False, point, ball, speed, res, text)
                except Exception as error:
                    print(error)
        sleep(2)


if __name__ == '__main__':
    authorization('login', 'password')
    # debug()  # - набирает текст с заданной скоростью, если зашёл в какой-то режим
    # qualification()  # - исправляет ошибки после квалификации
    start(['Обычный', 'По словарю «Лавка миров»'], True)
