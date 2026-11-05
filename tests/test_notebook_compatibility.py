"""Offline checks against the actual code embedded in both maintained notebooks."""
import ast
import json
from pathlib import Path
import types
import unittest
from unittest.mock import Mock

import nbformat
import pandas as pd
from pandas import json_normalize
from IPython.core.inputtransformer2 import TransformerManager

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_NAMES = ('MyPPSimulator_En.ipynb', 'MyPPSimulator_Beta_En_20250615_v5_0_8.ipynb')


def notebook(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def helper_namespace(name):
    source = next(''.join(c['source']) for c in notebook(name)['cells']
                  if 'def fetch_player_scores' in ''.join(c['source']))
    function = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'fetch_player_scores')
    request = Mock()
    namespace = {'requests': request, 'pd': pd, 'json_normalize': json_normalize,
                 'time': types.SimpleNamespace(sleep=lambda _: None)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<notebook-helper>', 'exec'), namespace)
    return namespace['fetch_player_scores'], request


def page(ids, total=5):
    response = Mock()
    response.json.return_value = {
        'playerScores': [{'score': {'id': i, 'timeSet': f'2026-11-0{i}T00:00:00Z'}} for i in ids],
        'metadata': {'total': total, 'itemsPerPage': 2},
    }
    return response


class NotebookCompatibilityTests(unittest.TestCase):
    def each_notebook(self):
        for name in NOTEBOOK_NAMES:
            yield name, helper_namespace(name)

    def test_full_pages_including_final_page(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                request.get.side_effect = [page([5, 4]), page([3, 2]), page([1])]
                self.assertEqual(fetch('test-player', 2)['score.id'].tolist(), [5, 4, 3, 2, 1])
                self.assertEqual([c.kwargs['params']['page'] for c in request.get.call_args_list], [1, 2, 3])

    def test_cache_overlap_updates_and_stops(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                request.get.side_effect = [page([5, 4]), page([3, 2])]
                cached = json_normalize(page([3, 2, 1]).json()['playerScores'])
                self.assertEqual(fetch('test-player', 2, cached)['score.id'].tolist(), [5, 4, 3, 2, 1])
                self.assertEqual(request.get.call_count, 2)

    def test_identical_latest_timestamp_terminates(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                request.get.return_value = page([5, 4])
                cached = json_normalize(page([5, 4]).json()['playerScores'])
                self.assertEqual(len(fetch('test-player', 2, cached)), 2)
                self.assertEqual(request.get.call_count, 1)

    def test_updated_existing_id_does_not_hide_next_page(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                first = page([3, 5])
                first.json.return_value['playerScores'][0]['score']['timeSet'] = '2026-11-06T00:00:00.123Z'
                request.get.side_effect = [first, page([4, 2])]
                cached = json_normalize(page([3, 2, 1]).json()['playerScores'])
                self.assertEqual(fetch('test-player', 2, cached)['score.id'].tolist(), [3, 5, 4, 2, 1])
                self.assertEqual(request.get.call_count, 2)

    def test_http_failure_is_not_silent_completion(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                bad = page([])
                bad.raise_for_status.side_effect = RuntimeError('HTTP 429')
                request.get.side_effect = [page([5, 4]), bad]
                with self.assertRaisesRegex(RuntimeError, '429'):
                    fetch('test-player', 2)

    def test_malformed_payload_is_not_ignored(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                request.get.return_value = Mock(json=lambda: {'error': 'bad request'})
                with self.assertRaisesRegex(ValueError, 'playerScores'):
                    fetch('test-player', 2)

    def test_empty_account_reports_missing_scores(self):
        for name, (fetch, request) in self.each_notebook():
            with self.subTest(notebook=name):
                request.get.return_value = page([], 0)
                with self.assertRaisesRegex(ValueError, 'No ScoreSaber'):
                    fetch('test-player', 2)

    def test_player_id_requires_input_and_preserves_long_ids(self):
        for name in NOTEBOOK_NAMES:
            with self.subTest(notebook=name):
                source = next(''.join(c['source']) for c in notebook(name)['cells']
                              if '\nplayer_id = ' in '\n' + ''.join(c['source']))
                start = source.index('player_id = ')
                # The input assignment, normalization and guard precede other inputs.
                nodes = ast.parse(TransformerManager().transform_cell(source[start:])).body[:3]
                self.assertEqual(nodes[0].value.value, '')
                guard = compile(ast.Module(body=nodes[1:], type_ignores=[]), '<player-id>', 'exec')
                for empty in ('', '  '):
                    with self.assertRaisesRegex(ValueError, 'player_id'):
                        exec(guard, {'player_id': empty})
                scope = {'player_id': ' 12345678901234567 '}
                exec(guard, scope)
                self.assertEqual(scope['player_id'], '12345678901234567')

    def test_notebooks_compile_without_saved_execution_data(self):
        transformer = TransformerManager()
        for name in NOTEBOOK_NAMES:
            with self.subTest(notebook=name):
                nb = nbformat.read(ROOT / name, as_version=4)
                nbformat.validate(nb)
                self.assertNotIn('widgets', nb.metadata)
                for i, cell in enumerate(nb.cells):
                    for key in ('outputId', 'executionInfo', 'ExecuteTime', 'colab'):
                        self.assertNotIn(key, cell.metadata)
                    if cell.cell_type == 'code':
                        self.assertEqual(cell.outputs, [])
                        self.assertIsNone(cell.execution_count)
                        compile(transformer.transform_cell(cell.source), f'{name}:cell{i}', 'exec')


if __name__ == '__main__':
    unittest.main()
