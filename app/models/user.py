from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    """
    Représente un utilisateur.

    Collection MongoDB : users
    {
        _id      : ObjectId (auto),
        username : str (unique),
        email    : str (unique),
        password : str (hashé)
    }
    """

    _id = fields.String(dump_only=True)
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=50)
    )
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=6)
    )
    joker_cards = fields.Integer(dump_only=True, dump_default=0)
    plus4_cards = fields.Integer(dump_only=True, dump_default=0)
    reverse_cards = fields.Integer(dump_only=True, dump_default=0)
    skip_cards = fields.Integer(dump_only=True, dump_default=0)