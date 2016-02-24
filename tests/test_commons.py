# -*- encoding: utf-8 -*-
import os
import shutil
import tempfile
import random
import unittest
import itertools
from strephit.commons import parallel, cache
from collections import Counter


class TestParallel(unittest.TestCase):
    def setUp(self):
        self.list_in = range(10)
        self.correct = set(map(self.function, self.list_in))
        self.list_in_nones = [x if x % 4 == 0 else None for x in xrange(20)]
        self.correct_nones = set(filter(self.none_filter, map(self.function,
                                        filter(self.none_filter, self.list_in_nones))))
        self.correct_multi = itertools.chain(*map(self.multi_function, self.list_in))

    def function(self, x):
        return 2 * x

    def none_filter(self, x):
        return x is not None

    def multi_function(self, x):
        for z in xrange(x):
            yield z

    def exc_function(self, x):
        raise ValueError('hello!')

    def consume(self, generator):
        [x for x in generator]

    def test_single_process(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=1))
        self.assertEqual(list_out, self.correct)

    def test_multi_process(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=2))
        self.assertEqual(list_out, self.correct)

    def test_with_nones_single_process(self):
        list_out = set(parallel.map(self.function, self.list_in_nones, processes=2))
        self.assertEqual(list_out, self.correct_nones)

    def test_with_nones_multi_process(self):
        list_out = set(parallel.map(self.function, self.list_in_nones, processes=1))
        self.assertEqual(list_out, self.correct_nones)

    def test_more_workers(self):
        list_out = set(parallel.map(self.function, self.list_in, processes=20))
        self.assertEqual(list_out, self.correct)

    def test_flatten_single_process(self):
        list_out = parallel.map(self.multi_function, self.list_in, processes=1,
                                flatten=True)
        self.assertEqual(Counter(list_out), Counter(self.correct_multi))

    def test_flatten_multi_process(self):
        list_out = parallel.map(self.multi_function, self.list_in, processes=2,
                                flatten=True)
        self.assertEqual(Counter(list_out), Counter(self.correct_multi))

    def test_exception_single(self):
        self.assertRaises(ValueError, self.consume,
                          parallel.map(self.exc_function, self.list_in, processes=1,
                                      raise_exc=True))


class TestCache(unittest.TestCase):
    def random_hex_string(self, length):
        return ''.join(random.choice('0123456789abcdef') for _ in xrange(6))

    @cache.cached
    def not_entirely_random_hex_string(self, length):
        return self.random_hex_string(length)

    def setUp(self):
        self.cache_loc = self.random_hex_string(8)
        cache.BASE_DIR = os.path.join(tempfile.gettempdir(), self.cache_loc)
        os.makedirs(cache.BASE_DIR)

    def tearDown(self):
        shutil.rmtree(cache.BASE_DIR)

    def test_path(self):
        hashed = 'hashed key'
        full, base, fname = cache._path_for(hashed)
        self.assertEqual(os.path.join(base, fname), full)
        self.assertEqual(os.path.commonprefix([cache.BASE_DIR, full, base]),
                         cache.BASE_DIR)

    def test_simple_get(self):
        self.assertIsNone(cache.get('non existing'))
        self.assertEqual(cache.get('non existing', 'default'), 'default')

    def test_simple_set(self):
        cache.set('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_set_overwrite(self):
        cache.set('key', 'value')
        cache.set('key', 'another value', overwrite=True)
        self.assertEqual(cache.get('key'), 'another value')
        cache.set('key', 'something else', overwrite=False)
        self.assertEqual(cache.get('key'), 'another value')

    def test_decorator(self):
        val = self.not_entirely_random_hex_string(128)
        for _ in xrange(10):
            self.assertEqual(val, self.not_entirely_random_hex_string(128))

    def test_unicode(self):
        cache.set(u'蓄えて ください',  u'お疲れさま')
        self.assertEqual(cache.get(u'蓄えて ください', u'お疲れさま'),
                         u'お疲れさま')