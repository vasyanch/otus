#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import json


def get_score(store, phone=None, email=None, birthday=None, gender=None, first_name=None, last_name=None):
    key_parts = [
        first_name.encode('utf-8') if first_name is not None else "",
        last_name.encode('utf-8') if last_name is not None else "",
        phone.encode('utf-8') if phone is not None else "",
        birthday.strftime("%Y%m%d") if birthday is not None else "",
        str(gender) if gender is not None else "",
        email.encode('utf-8') if email is not None else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts)).hexdigest()
    # try get from cache,
    # fallback to heavy calculation in case of cache miss
    value = store.cache_get(key)
    score = float(value) if value else 0
    if score:
        return score
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    # cache for 60 minutes
    store.cache_set(key, score, 60 * 60)
    return score


def get_interests(store, cid):
    r = store.get("i:%s" % cid)
    return json.loads(r) if r else []
