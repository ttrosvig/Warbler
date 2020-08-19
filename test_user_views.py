"""User View tests"""

from unittest import TestCase
from models import db, connect_db, Message, User, Likes, Follows
from app import app, CURR_USER_KEY
from secret import PASSWORD

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{PASSWORD}@localhost/warbler-test'

db.create_all()

app.config['WTF_CSRF_ENABLED'] = False

class MessageViewTestCase(TestCase):
  """Test views for messages."""

  def setUp(self):
    """Create test client, add sample data."""

    db.drop_all()
    db.create_all()

    self.client = app.test_client()

    self.testuser = User.signup(username="testuser",
      email="test@test.com",
      password="testuser",
      image_url=None)
      
    self.testuser_id = 8989
    self.testuser.id = self.testuser_id

    self.u1 = User.signup("abc", "test1@test.com", "password", None)
    self.u1_id = 778
    self.u1.id = self.u1_id

    self.u2 = User.signup("efg", "test2@test.com", "password", None)
    self.u2_id = 884
    self.u2.id = self.u2_id

    self.u3 = User.signup("hij", "test3@test.com", "password", None)
    self.u4 = User.signup("testing", "test4@test.com", "password", None)

    db.session.commit()

  def tearDown(self):
    resp = super().tearDown()
    db.session.rollback()
    return resp

  def test_user_show(self):
    with self.client as c:
      resp = c.get(f"/users/{self.testuser_id}", follow_redirects=True)

      self.assertEqual(resp.status_code, 200)

  def setup_likes(self):
    m1 = Message(text="trending warble", user_id=self.testuser_id)
    
    m2 = Message(text="Eating some lunch", user_id=self.testuser_id)

    m3 = Message(id=9876, text="likable warble", user_id=self.u1_id)

    db.session.add_all([m1, m2, m3])
    db.session.commit()

    l1 = Likes(user_id=self.testuser_id, message_id=9876)

    db.session.add(l1)
    db.session.commit()

  def test_add_like(self):
    m = Message(id=1984, text="The earth is round", user_id=self.u1_id)
    db.session.add(m)
    db.session.commit()

    with self.client as c:
      with c.session_transaction() as sess:
          sess[CURR_USER_KEY] = self.testuser_id

      resp = c.post("/messages/1984/like", follow_redirects=True)

      self.assertEqual(resp.status_code, 200)

      likes = Likes.query.filter(Likes.message_id==1984).all()

      self.assertEqual(len(likes), 1)

      self.assertEqual(likes[0].user_id, self.testuser_id)

  def test_remove_like(self):
    self.setup_likes()

    m = Message.query.filter(Message.text=="likable warble").one()

    self.assertIsNotNone(m)

    self.assertNotEqual(m.user_id, self.testuser_id)

    l = Likes.query.filter(
        Likes.user_id==self.testuser_id and Likes.message_id==m.id
    ).one()

    self.assertIsNotNone(l)

    with self.client as c:
      with c.session_transaction() as sess:
        sess[CURR_USER_KEY] = self.testuser_id

      resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)

      self.assertEqual(resp.status_code, 200)

      likes = Likes.query.filter(Likes.message_id==m.id).all()

      # The like has been deleted
      self.assertEqual(len(likes), 0)

  def test_unauthenticated_like(self):
    self.setup_likes()

    m = Message.query.filter(Message.text=="likable warble").one()
    self.assertIsNotNone(m)

    like_count = Likes.query.count()

    with self.client as c:
      resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)

      self.assertEqual(resp.status_code, 200)

      self.assertIn("Access unauthorized", str(resp.data))

      # The number of likes has not changed since making the request
      self.assertEqual(like_count, Likes.query.count())

  def setup_followers(self):
    f1 = Follows(user_being_followed_id=self.u1_id, user_following_id=self.testuser_id)

    f2 = Follows(user_being_followed_id=self.u2_id, user_following_id=self.testuser_id)

    f3 = Follows(user_being_followed_id=self.testuser_id, user_following_id=self.u1_id)

    db.session.add_all([f1,f2,f3])
    db.session.commit()

  def test_show_followers(self):

    self.setup_followers()
    with self.client as c:
      with c.session_transaction() as sess:
        sess[CURR_USER_KEY] = self.testuser_id

      resp = c.get(f"/users/{self.testuser_id}/followers")

      self.assertIn("@abc", str(resp.data))

      self.assertNotIn("@efg", str(resp.data))

      self.assertNotIn("@hij", str(resp.data))

      self.assertNotIn("@testing", str(resp.data))

  def test_unauthorized_following_page_access(self):
      self.setup_followers()
      with self.client as c:

        resp = c.get(f"/users/{self.testuser_id}/following", follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        self.assertNotIn("@abc", str(resp.data))

        self.assertIn("Access unauthorized", str(resp.data))

  def test_unauthorized_followers_page_access(self):
    self.setup_followers()
    with self.client as c:

      resp = c.get(f"/users/{self.testuser_id}/followers", follow_redirects=True)

      self.assertEqual(resp.status_code, 200)

      self.assertNotIn("@abc", str(resp.data))

      self.assertIn("Access unauthorized", str(resp.data))