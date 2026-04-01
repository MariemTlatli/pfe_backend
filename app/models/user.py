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