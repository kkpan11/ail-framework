#!/usr/bin/env python3
# -*-coding:UTF-8 -*

'''
    Blueprint Flask: crawler splash endpoints: dashboard, onion crawler ...
'''

import json
import os
import sys

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for, Response, abort, send_file
from flask_login import login_required, current_user

# Import Role_Manager
from Role_Manager import login_admin, login_user, login_read_only

sys.path.append(os.environ['AIL_BIN'])
##################################
# Import Project packages
##################################
from lib.ail_core import paginate_iterator
from lib.objects import Mails
from packages import Date
from lib import search_engine

# ============ BLUEPRINT ============
objects_mail = Blueprint('objects_mail', __name__, template_folder=os.path.join(os.environ['AIL_FLASK'], 'templates/objects/mail'))

# ============ VARIABLES ============
bootstrap_label = ['primary', 'success', 'danger', 'warning', 'info']

# ============ FUNCTIONS ============
def create_json_response(data, status_code):
    return Response(json.dumps(data, indent=2, sort_keys=True), mimetype='application/json'), status_code

# ============= ROUTES ==============
@objects_mail.route("/objects/mails", methods=['GET'])
@login_required
@login_read_only
def objects_mails():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    show_objects = request.args.get('show_objects')
    date = Date.sanitise_date_range(date_from, date_to)
    date_from = date['date_from']
    date_to = date['date_to']

    if show_objects:
        dict_objects = Mails.Mails().api_get_meta_by_daterange(date_from, date_to)
    else:
        dict_objects = {}

    return render_template("MailDaterange.html", date_from=date_from, date_to=date_to,
                           dict_objects=dict_objects, show_objects=show_objects)

@objects_mail.route("/objects/mail/post", methods=['POST'])
@login_required
@login_read_only
def objects_mails_post():
    date_from = request.form.get('date_from')
    date_to = request.form.get('date_to')
    show_objects = request.form.get('show_objects')
    return redirect(url_for('objects_mail.objects_mails', date_from=date_from, date_to=date_to, show_objects=show_objects))

@objects_mail.route("/objects/mail/range/json", methods=['GET'])
@login_required
@login_read_only
def objects_mail_range_json():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    date = Date.sanitise_date_range(date_from, date_to)
    date_from = date['date_from']
    date_to = date['date_to']
    return jsonify(Mails.Mails().api_get_chart_nb_by_daterange(date_from, date_to))

@objects_mail.route("/objects/mail/search_post", methods=['POST'])
@login_required
@login_user
def objects_mail_search_post():
    to_search = request.form.get('to_search')
    if to_search:
        to_search = to_search.lower()
    # search_type = request.form.get('search_type', 'id')
    # case_sensitive = False
    page = request.form.get('page', 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    return redirect(url_for('objects_mail.objects_mail_search', search=to_search, page=page))

@objects_mail.route("/objects/mail/search", methods=['GET'])
@login_required
@login_user
def objects_mail_search():
    user_id = current_user.get_user_id()
    to_search = request.args.get('search')
    page = request.args.get('page', 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    mails = Mails.Mails()

    if to_search:
        to_search = to_search.lower()

    # if type_to_search == 'id':
    #     if len(type_to_search) == 64:
    #         mail = Mails.Mail(to_search)
    #         if not mail.exists():
    #             abort(404)
    #         else:
    #             return redirect(mail.get_link(flask_context=True))
    #     else:
    #         search_result = mails.search_by_id(to_search, r_pos=True, case_sensitive=False)
    # elif type_to_search == 'content':
    search_engine.log(user_id, 'mail', to_search)
    search_result = mails.search_by_content(to_search, r_pos=True, case_sensitive=False, regex=False)
    # else:
    #     return create_json_response({'error': 'Unknown search type'}, 400)

    if search_result:
        ids = sorted(search_result.keys())
        dict_page = paginate_iterator(ids, nb_obj=500, page=page)
        dict_objects = mails.get_metas(dict_page['list_elem'], options={'sparkline'})
    else:
        dict_objects = {}
        dict_page = {}

    return render_template("search_mail_result.html", dict_objects=dict_objects, search_result=search_result,
                           dict_page=dict_page,
                           to_search=to_search)

