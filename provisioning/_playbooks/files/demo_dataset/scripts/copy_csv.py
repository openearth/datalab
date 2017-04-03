import os
from shutil import copy2

def copy_csv(results_dir):
    """
    Add csv file to results directory
    """
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    copy2(
        os.path.join(os.path.dirname(__file__), '..', 'raw', 'xyztext.csv'),
        results_dir
    )

if __name__ == '__main__':
    results_dir = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'results',
    )
    print 'Storing results in: {0}'.format(results_dir)
    copy_csv(results_dir=results_dir)
    print 'copied xyztext.csv.'