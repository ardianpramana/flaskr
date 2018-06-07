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

    """ Get likes total """
    likes_list = []
    comments_list = []
    for post in posts:
        likes = db.execute(
            'SELECT id, post_id, is_like FROM likes WHERE post_id=? and is_like=1', (post['id'],)
        ).fetchall()
        likes_list.append(len(likes))

        comments = db.execute(
            'SELECT id FROM comments WHERE post_id=?', (post['id'],)
        ).fetchall()
        comments_list.append(len(comments))

    data = {
        'posts': posts,
        'likes_list': likes_list,
        'comments_list': comments_list,
    }

    print(data['comments_list'])

    return render_template('blog/index.html', posts=posts, data=data)


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


@bp.route('/<int:id>/post', methods=('GET', 'POST'))
def post_detail(id):
    post = get_post_detail(id)
    db = get_db()

    if request.method == 'POST':
        visitor = request.form['name']
        comment = request.form['comment']
        error = None
        if not visitor:
            error = 'Your name is required.'
        if not comment:
            error = 'Comment is required.'
        if error is not None:
            flash(error)

        db.execute(
            'INSERT INTO comments (post_id, visitor, comment)'
            ' VALUES (?, ?, ?)',
            (id, visitor, comment)
        )
        db.commit()

    is_like = False
    if g.user:
        like_detail = get_likes_detail(post['id'], g.user['id'])
        if like_detail:
            is_like = like_detail['is_like']
        else:
            is_like = False
    likes_count = get_likes_count(id)

    """ Get comment if exists """
    comments = db.execute(
        'SELECT id, created, post_id, visitor, comment'
        ' FROM comments WHERE post_id = ?', (id,)
    ).fetchall()

    comment_count = 0
    if comments:
        comment_count = len(comments)

    data = {
        'likes_count': likes_count,
        'is_like': is_like,
        'post': post,
        'comments': comments,
        'comment_count': comment_count,
    }

    return render_template('blog/post_detail.html', data=data)


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
