from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)


@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    # posts = db.execute(
    #     'SELECT po.id, po.created, po.title, po.body, count(lk.is_like)'
    #     'FROM ('
    #     'SELECT p.id, title, body, created FROM post p JOIN user u ON p.author_id = u.id ORDER BY created DESC'
    #     ') po JOIN likes lk ON po.id = lk.post_id WHERE lk.is_like = 1 GROUP BY lk.post_id'
    # ).fetchall()

    return render_template('blog/index.html', posts=posts)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/post')
def post_detail(id):
    post = get_post_detail(id)
    is_like = False

    if g.user:
        print('g has user, running like_detail')
        like_detail = get_likes_detail(post['id'], g.user['id'])
        if like_detail:
            is_like = like_detail['is_like']
        else:
            is_like = False

    likes_count = get_likes_count(id)

    return render_template('blog/post_detail.html', post=post, is_like=is_like, likes_count=likes_count)


@bp.route('/<int:post_id>/like')
@login_required
def like_this_post(post_id):
    if g.user['id']:
        is_like = True
        like_detail = get_likes_detail(post_id, g.user['id'])

        if not like_detail:
            db = get_db()
            db.execute(
                'INSERT INTO likes (post_id, user_id, is_like)'
                ' VALUES (?, ?, ?)',
                (post_id, g.user['id'], is_like)
            )
            db.commit()
        else:
            is_like = like_detail['is_like']
            if not is_like:
                is_like = True
            else:
                is_like = False

            db = get_db()
            db.execute(
                'UPDATE likes SET is_like = ?'
                ' WHERE id = ?',
                (is_like, like_detail['id'])
            )
            db.commit()

    return redirect(url_for('blog.post_detail', id=post_id))


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


def get_post_detail(id):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    return post


def get_likes_detail(post_id, user_id):
    like_detail = get_db().execute(
        'SELECT id, post_id, user_id, is_like FROM likes WHERE post_id = ? and user_id = ?',
        (post_id, user_id)
    ).fetchone()

    return like_detail


def get_likes_count(post_id):
    likes_count = 0
    likes = get_db().execute(
        'SELECT id, is_like FROM likes WHERE post_id = ?', (post_id,)
    )
    for rec in likes:
        if rec['is_like']:
            likes_count += 1

    return likes_count
