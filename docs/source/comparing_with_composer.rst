Comparing with PHP's Composer library
=====================================

First, clone composer's somewhere on your machine::

    git clone https://github.com/composer/composer

Then, use the ``scripts/scenario_to_php.py`` script to write a PHP file that
will print the composer's solution for a given scenario::

    python scripts/scenario_to_php.py \
        --composer-root <path to composer github checkout> \
        simplesat/tests/simple_numpy.yaml \
        scripts/print_operations.php.in

    python scripts/scenario_to_php.py \
        --composer-root <path to composer github checkout> \
        simplesat/tests/simple_numpy.yaml \
        scripts/print_rules.php.in

This will create ``scripts/print_operations.php`` and
``scripts/print_rules.php`` scripts you can simply execute with ``php``::

    php scripts/print_rules.php
    php scripts/print_operations.php
