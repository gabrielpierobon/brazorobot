from flask import Flask, render_template, request, redirect, url_for, session
import requests
import csv
import pandas as pd
from flask import make_response
from io import BytesIO
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def get_card_images():
    url = 'https://api.scryfall.com/cards/random'
    response = requests.get(url)
    if response.status_code == 200:
        card_data_1 = response.json()
        if 'image_uris' in card_data_1:
            card_image_1 = card_data_1['image_uris']['normal']
            card_name_1 = card_data_1['name']
            card_set_1 = card_data_1['set_name']
            card_rarity_1 = card_data_1['rarity']

            response = requests.get(url)
            if response.status_code == 200:
                card_data_2 = response.json()
                if 'image_uris' in card_data_2:
                    card_image_2 = card_data_2['image_uris']['normal']
                    card_name_2 = card_data_2['name']
                    card_set_2 = card_data_2['set_name']
                    card_rarity_2 = card_data_2['rarity']

                    card_images_and_names = [(card_name_1, card_image_1, card_set_1, card_rarity_1),
                                             (card_name_2, card_image_2, card_set_2, card_rarity_2)]
                    return card_images_and_names

    return None


@app.route('/', methods=['GET'])
def home():
    with open('blog_posts.json', 'r') as file:
        blog_posts = json.load(file)
    return render_template('home.html', blog_posts=blog_posts)


@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'selected_images' not in session:
        session['selected_images'] = []
    if 'unselected_images' not in session:
        session['unselected_images'] = []

    if request.method == 'POST':
        selected_cards = request.form.getlist('selected')
        session['selected_images'].extend(
            card for card in session['card_images'] if card[1] in selected_cards
        )
        session['unselected_images'].extend(
            card for card in session['card_images'] if card[1] not in selected_cards
        )
        session.pop('card_images', None)

    if 'card_images' not in session or not session['card_images']:
        card_images = get_card_images()
        if card_images is None:
            # Handle the case when card_images is None
            # You can redirect the user to an error page or display a message
            # Here, we redirect the user back to the home page
            return redirect(url_for('home'))
        session['card_images'] = card_images

    return render_template('game.html',
                           card_images=session.get('card_images', []),
                           selected_images=session.get('selected_images', []),
                           unselected_images=session.get('unselected_images', []))


@app.route('/summary')
def summary():
    return render_template('summary.html',
                           selected_images=session.get('selected_images', []),
                           unselected_images=session.get('unselected_images', []))


@app.route('/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return redirect(url_for('game'))


@app.route('/download/csv', methods=['GET'])
def download_csv():
    selected_cards = session.get('selected_images', [])
    si = [list(i) for i in selected_cards]
    si.insert(0, ['Card Name', 'Card Image URL', 'Set Name', 'Rarity'])

    si = [",".join(map(str, i)) for i in si]
    output = "\n".join(si)

    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=selected_cards.csv"
    response.headers["Content-type"] = "text/csv"

    return response


@app.route('/download/xls')
def download_xls():
    # Create DataFrame from selected images
    df = pd.DataFrame(session.get('selected_images', []), columns=['Card Name', 'Card Image URL', 'Set Name', 'Rarity'])

    # Create a BytesIO object, save the Excel file there
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    writer.book.close()  # Close the xlsxwriter Workbook object, not the pd.ExcelWriter object
    output.seek(0)

    # Create a Flask response with the Excel file
    resp = make_response(output.read())
    resp.headers["Content-Disposition"] = "attachment; filename=export.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return resp





if __name__ == '__main__':
    app.run(debug=False)
