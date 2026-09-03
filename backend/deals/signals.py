"""
Deal signal hooks.

Deal creation is intentionally NOT triggered from Viewing.post_save.

The controlled transaction flow is:

    confirmed viewing
    -> complete_viewing()
    -> viewing completed
    -> Property Introduction Certificate
    -> Deal

Keeping Deal creation inside the explicit viewing completion service avoids
creating a Deal before the Property Introduction Certificate exists.
"""