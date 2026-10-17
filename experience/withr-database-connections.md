withr database connection proofs use SQLAlchemy `Connection` objects and
explicit `scope()` for `local_db_connection`; both lifecycle helpers observe
closure through the connection's `closed` property.
