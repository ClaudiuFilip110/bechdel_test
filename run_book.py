from pyvis.network import Network
from bs4 import BeautifulSoup
import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import argparse
 
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("src", type=str, help="Source location")
args = parser.parse_args()
config = vars(args)

def prune_names(b):
    b = b.strip()
    if len(b.split()) > 2:
        return
    if not b.isupper():
        return
    for word in b.split():
        if not word.isalpha():
            return
    return b.strip().split()


def is_female(full_name):
    for character in female_characters:
        if character in full_name:
            return True
    return False


def speaking_about_male(text):
    for male in male_characters:
        if male in text.upper():
            return True
    return False


def disc_length(text):
    return len(text.split())

book_name = args.src
f = open("data/"+book_name, "r")
html_doc = f.read()

soup = BeautifulSoup(html_doc, 'html.parser')

set_of_bs = set([tag.string for tag in soup.find_all('b')])  # get all b tags
bs = list(set_of_bs)

characters_names = []
for b in bs:
    if prune_names(b):
        characters_names.append(' '.join(prune_names(b)))


url = 'https://namecensus.com/first-names/common-female-first-names/'

female_names = []

req = requests.get(url)

soup = BeautifulSoup(req.content, 'html.parser')
table = soup.find(
    'table', attrs={'class': 'table is-narrow is-bordered is-fullwidth mb-3'})
table_body = table.find('tbody')
rows = table_body.find_all('tr')

for row in rows:
    cols = row.find_all('td')
    cols = [ele.text.strip() for ele in cols]
    female_names.append(cols[1])

# extend and add the titles
female_names.extend(['MISS ', 'MRS. ', 'MS. ', 'MA\'AM ', 'WOMAN'])
female_names.sort()


url = 'https://namecensus.com/first-names/common-male-first-names/'

male_names = []

req = requests.get(url)
soup = BeautifulSoup(req.content, 'html.parser')
table = soup.find(
    'table', attrs={'class': 'table is-narrow is-bordered is-fullwidth mb-3'})
table_body = table.find('tbody')
rows = table_body.find_all('tr')

for row in rows:
    cols = row.find_all('td')
    cols = [ele.text.strip() for ele in cols]
    male_names.append(cols[1])

# extend and add the titles
male_names.extend(['MR ', 'MISTER '])
male_names.sort()


female_characters = []  # list of all female characters
for female in female_names:
    for character_name in characters_names:
        if female in character_name:
            female_characters.append(character_name)

male_characters = []  # list of all male characters
for male in male_names:
    for character_name in characters_names:
        if male in character_name and male not in female_names:
            male_characters.append(character_name)

female_characters = list(set(female_characters))  # remove duplicates
male_characters = list(set(male_characters))  # remove duplicates

df = pd.DataFrame(columns=['female_speaking', 'text',
                  'female_speaking_to_female', 'speaking_about_male'])

f = open("data/8MM.html", "r")  # have to init. BeautifulSoup again
html_doc = f.read()
soup = BeautifulSoup(html_doc, 'html.parser')

for x in soup.find_all('b'):
    if prune_names(x.text):
        df = df.append({
            'female_speaking': ' '.join(prune_names(x.text)),
            'text': x.next_sibling,
            'female_speaking_to_female': False,
            'speaking_about_male': False},
            ignore_index=True)


df = df[df['female_speaking'].apply(is_female)]  # leave only female

for i in range(len(df)-1):
    if is_female(df.iloc[i+1, 0]):  # check if there is a woman is speaking to another woman
        df.iloc[i, 2] = True

df['speaking_about_male'] = df['text'].apply(
    speaking_about_male)  # check if they're speaking about males

# remove dialogues where there aren't two females talking OR they're talking about a male
df = df[df['female_speaking_to_female'] & df['speaking_about_male'] == False]

# length of each dialogue
df['disc_length'] = df['text'].apply(disc_length)

nr_female_chars = len(female_characters)
female_to_female_discs = len(df)-1
average_disc_length = df['disc_length'].mean()
print('Nr of female characters: ', nr_female_chars)
print('Nr of female to female discussions: ', female_to_female_discs)
print('The average number of words in each discussion: ', average_disc_length)

relationships = []

for i in range(len(df)-1):
    relationships.append({"source": df.iloc[i, 0], "target": df.iloc[i+1, 0]})
relationship_df = pd.DataFrame(relationships)
relationship_df["value"] = 1
relationship_df = relationship_df.groupby(
    ["source", "target"], sort=False, as_index=False).sum()

# Create a graph from a pandas dataframe
G = nx.from_pandas_edgelist(relationship_df,
                            source="source",
                            target="target",
                            edge_attr="value",
                            create_using=nx.Graph())

plt.figure(figsize=(10, 10))
pos = nx.kamada_kawai_layout(G)
nx.draw(G, with_labels=True, node_color='skyblue',
        edge_cmap=plt.cm.Blues, pos=pos)
# plt.show()
net = Network(notebook=True, width="1000px", height="700px",
              bgcolor='#222222', font_color='white')

node_degree = dict(G.degree)

# Setting up node size attribute
nx.set_node_attributes(G, node_degree, 'size')

net.from_nx(G)
net.show(book_name)
