import os

def fill_dir_with_bogus_files(results_dir, amount=4, ext='.nc'):
    """
    Fill directory with result-<num><ext> files.
    """
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    flist = []
    for n in range(0, amount):
        fpath = os.path.join(
            results_dir, 'result-{0}{1}'.format(n, ext)
        )
        print('Creating file "{0}"'.format(fpath))
        open(fpath, 'a').close()
        flist.append(fpath)

    return flist

if __name__ == '__main__':

    results_dir = os.path.join(
        os.path.dirname(__file__),
        '../../',
        '..',
        'results',
    )
    print 'Storing results in: {0}'.format(results_dir)
    fill_dir_with_bogus_files(results_dir=results_dir)
    fill_dir_with_bogus_files(results_dir=results_dir, ext='.m')