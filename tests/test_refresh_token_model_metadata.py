import unittest

from sqlalchemy import UniqueConstraint

from app.models.refresh_token import RefreshToken


class RefreshTokenModelMetadataTestCase(unittest.TestCase):
    def test_token_hash_uses_unique_constraint_without_duplicate_index(self) -> None:
        table = RefreshToken.__table__
        unique_column_sets = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }

        self.assertIn(("token_hash",), unique_column_sets)
        self.assertNotIn(
            "ix_refresh_tokens_token_hash",
            {index.name for index in table.indexes},
        )


if __name__ == "__main__":
    unittest.main()
