from app.osm import _build_query, aggregate_categories, vibrancy_index


def test_build_query_uses_exact_match_not_regex():
    query = _build_query(45.76, 4.83, 400)
    assert "~" not in query
    assert 'node["shop"]' in query
    assert 'node["amenity"="restaurant"]' in query
    assert "around:400,45.76,4.83" in query


def test_aggregate_categories_buckets_by_tag():
    elements = [
        {"tags": {"shop": "bakery"}},
        {"tags": {"shop": "supermarket"}},
        {"tags": {"amenity": "restaurant"}},
        {"tags": {"amenity": "cafe"}},
        {"tags": {"amenity": "pharmacy"}},
        {"tags": {"amenity": "school"}},
        {"tags": {"amenity": "bank"}},
        {"tags": {"public_transport": "stop_position"}},
        {"tags": {"amenity": "parking"}},  # not tracked, should be ignored
    ]
    counts = aggregate_categories(elements)
    assert counts == {
        "commerces": 2,
        "restauration": 2,
        "sante": 1,
        "education": 1,
        "services_bancaires": 1,
        "transport": 1,
    }


def test_aggregate_categories_empty_input():
    counts = aggregate_categories([])
    assert all(v == 0 for v in counts.values())


def test_vibrancy_index_is_capped_at_100():
    counts = {
        "commerces": 100,
        "restauration": 100,
        "sante": 100,
        "education": 100,
        "services_bancaires": 100,
        "transport": 100,
    }
    assert vibrancy_index(counts) == 100


def test_vibrancy_index_zero_for_empty_area():
    counts = {k: 0 for k in ["commerces", "restauration", "sante", "education", "services_bancaires", "transport"]}
    assert vibrancy_index(counts) == 0


def test_vibrancy_index_weights_transport_more_than_commerce():
    base = {"commerces": 0, "restauration": 0, "sante": 0, "education": 0, "services_bancaires": 0, "transport": 0}
    one_shop = {**base, "commerces": 1}
    one_transport = {**base, "transport": 1}
    assert vibrancy_index(one_transport) > vibrancy_index(one_shop)
