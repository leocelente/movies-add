import os
from string import Template
import requests
import json
from bs4 import BeautifulSoup
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
import PySimpleGUI as sg

autodownload = False
apikey = "<RADARR-API-KEY>"
server = "<RADARR-SERVER-IP-AND-PORT>"
url_lookup = Template(
        "http://"+ server +"/api/movie/$endpoint?imdbId=$imdbid&apikey=$apikey")

def GetMovieFromIMDBid(imdbId):
    endpoint = "lookup/imdb"
    
    url = (url_lookup.substitute(
        endpoint=endpoint, imdbid=imdbId, apikey=apikey))
    results_string = requests.get(url).content
    try:
        movie = json.loads(results_string)
        assert(movie["tmdbId"])
    except ValueError:
        print("Failed IMDB lookup")
        return -1
    return movie


def GetImdbidFromSEARCH(search_term):
    url_template = Template(
        "http://yts.lt/api/v2/list_movies.json?query_term=$term")
    url = url_template.substitute(term=search_term)
    results_string = requests.get(url).content
    results = json.loads(results_string)["data"]["movies"]
    imdb_ids = []
    for movie in results:
        imdb_ids.append({"imdbid": movie["imdb_code"], "title": movie['title'],
                         "year": movie['year'], "poster": movie["large_cover_image"]})
    return imdb_ids


def AddMovieFromIDMBid(imdbid):
    header = {
        "X-Api-Key": apikey,
        "Content-Type": "application/json"
    }
    url = "http://"+ server +"/api/movie"
    movie = GetMovieFromIMDBid(imdbid)
    if movie == -1:
        exit
    
    data = {
        "title": movie["title"],
        "qualityProfileId": 1,  # movie["qualityProfileId"],
        "titleSlug": movie["titleSlug"],
        "images": movie["images"],
        "tmdbId": movie["tmdbId"],
        "year": movie["year"],
        "rootFolderPath": "F:\\Media\\Movies",
        "monitored": autodownload,
        "addOptions": {
            "searchForMovie": autodownload
        }
    }
    data = json.dumps(data)
    results_string = requests.post(url, data=data, headers=header)
    return (json.loads(results_string.content))


class Subtitle(object):
    votes = 0
    link = ""
    language = ""

    def __init__(self, entry):
        self.votes = entry[0]
        self.language = entry[1]
        slug = entry[2]
        self.link = "http://yifysubtitles.com/subtitle/" + slug + ".zip"

    def __repr__(self):
        t = Template("{votes=$votes, language=$language, link=$link }")
        return t.substitute(votes=self.votes, language=self.language, link=self.link)

    def __str__(self):
        t = Template("{votes=$votes, language=$language, link=$link }")
        return t.substitute(votes=self.votes, language=self.language, link=self.link)


def GetSubtitles(imdbid):
    url_template = Template("http://yts-subs.com/movie-imdb/$imdbid")
    url = url_template.substitute(imdbid=imdbid)
    html = requests.get(url).content

    def parse_row(element):
        links = element.find_all('a')
        if len(links):
            if links[0].get_attribute_list('class')[0] == None:
                link = links[0]['href'].split('/')[2]
                return link
        return element.text.strip()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find(class_="other-subs")
    table_body = table.find('tbody')

    data = []
    rows = table_body.find_all('tr')

    for row in rows:
        cols = row.find_all('td')
        cols = [parse_row(element) for element in cols]
        data.append([element for element in cols if element])
    subs = []
    for d in data:
        s = Subtitle(d)
        subs.append(s)
    return subs


def DownloadUnzip(url):
    file_name = os.path.basename(url)
    try:
        f = urlopen(url)
        with open(file_name, "wb") as local_file:
            local_file.write(f.read())
    except OSError:
        exit
    except EnvironmentError :
        exit
    with ZipFile(file_name, 'r') as zip:
        zip.printdir()
        # print('Extracting all the files now...')
        zip.extractall()
    os.remove(file_name)
    print('Done!')




movie_t = Template("$title ($year)")
sub_t = Template("$language  (votes: $votes)")

# name = input("Name of the Movie: ")
# results = GetImdbidFromSEARCH(name)
# for i in range(len(results)):
#     print(movie_t.substitute(
#         id=i, title=results[i]["title"], year=results[i]["year"]))
# id = int(input("Enter the id: "))
# imdbid = results[id]["imdbid"]
# print("Adding to Radarr and Plex...")
# AddMovieFromIDMBid(imdbid)
# print("Done.")
# print("Searchig for subtitles")
# subs = GetSubtitles(imdbid)
# for i in range(len(subs)):
#     if subs[i].language == "Brazilian portuguese" or subs[i].language == "English":
#         print(sub_t.substitute(
#             id=i, language=subs[i].language, votes=subs[i].votes))
# id = int(input("Enter the id: "))
# print("Downloading Subtitle:")
# DownloadUnzip(subs[id].link)

movies = []
subs = []
sg.theme('Dark Blue 3')  # please make your windows colorful

layout = [[sg.Text('Titulo do Filme (em ingles):')],
          [sg.Input(key='_IN_', size=(48, 1))],
          [sg.Button('Search')],
          [sg.Listbox(values=movies, size=(46, 8), key='_LB_Movies')],
          [sg.Button("Add", disabled=True), sg.Button("Find Subtitles", disabled=True)],
          [sg.Listbox(values=subs, size=(46, 8), key='_LB_Subs')],
          [sg.Button("Download", disabled=True), sg.Button("Exit")],
          [sg.Text(size=(48,3), key='_OUTPUT_')]
          ]

window = sg.Window('Movie Adder', layout)

while True:  # Event Loop
    event, values = window.read()       # can also be written as event, values = window()
    # print(event, values)
    if event is None or event == 'Exit':
        break

    if event == 'Search':
        window['_OUTPUT_']("Searching for Movie" +  str(values['_IN_']) + "...")
        movies = GetImdbidFromSEARCH(values['_IN_'])
        data = []
        for movie in movies:
            data.append(movie_t.substitute(title=movie["title"], year=movie["year"]))
        if len(movies):
            window["Add"].update(disabled=False)
        window["_LB_Movies"].update(data)
        window['_OUTPUT_']("Done")

    if event == 'Add':
        window['_OUTPUT_']("Adding Movie ...")
        if len(movies):
            idx = (window["_LB_Movies"].GetIndexes())[0]
            movie = movies[idx]
            AddMovieFromIDMBid(movie["imdbid"])
            window["Find Subtitles"].update(disabled=False)
        window['_OUTPUT_']("Done")

    if event == 'Find Subtitles':
        window['_OUTPUT_']("Searching for Subtitles ...")
        if len(movies):
            idx = (window["_LB_Movies"].GetIndexes())[0]
            movie = movies[idx]
            subs = GetSubtitles(movie["imdbid"])
            if len(subs):
                data = []
                for sub in subs:
                    if sub.language == "Brazilian portuguese" or sub.language == "English":
                        data.append(sub_t.substitute(language=sub.language, votes=sub.votes))
                window["_LB_Subs"].update(data)
                window["Download"].update(disabled=False)
        window['_OUTPUT_']("Done")
    if event == "Download":
        window['_OUTPUT_']("Downloading and Extracting Subtitle")
        if len(subs):
            idx = (window["_LB_Subs"].GetIndexes())[0]
            sub = subs[idx]
            DownloadUnzip(sub.link)
        window['_OUTPUT_']("Copie o arquivo .srt (legenda) para a pasta:\n 1TB na Rede\\Media\\Movies\\<Nome do Filme> ")
window.close()