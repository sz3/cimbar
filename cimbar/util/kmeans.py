import json
import sys

import pandas as pd


def dist(x, y):
    return sum((xi - yi) ** 2 for xi, yi in zip(x, y))


def recompute_cluster_labels(data, centers):
    labels = []
    for point in data:
        distances = [dist(point, center) for center in centers]
        labels.append(distances.index(min(distances)))
    return labels


class kmeans():
    def __init__(self, data, columns, num_clusters, init_centers=None):
        self.num_clusters = num_clusters
        self.df = pd.DataFrame(data)
        self.df.columns = columns

        self.centers = init_centers or self.df.sample(num_clusters)  # random center
        print(self.centers)
        self.labels = self._compute_labels()

    def _compute_labels(self):
        return recompute_cluster_labels(self.df[self.df.columns].values, self.centers[self.df.columns].values)

    def update(self):
         self.centers = self.df[self.df.columns].groupby(self.labels).mean()
         print(self.centers)
         self.labels = self._compute_labels()

    def plot(self, filename):
        from matplotlib import pyplot

        x, y, z = self.df.columns

        fig = pyplot.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(self.df[x], self.df[y], self.df[z], c=self.labels)
        ax.set_ylim(ax.get_ylim()[::-1])
        pyplot.xlabel(x)
        pyplot.ylabel(y)
        fig.savefig(filename)


def _fake_data():
    from sklearn.datasets import make_blobs
    data, _ = make_blobs(n_samples=300,
                         n_features=3,
                         centers=4,
                         random_state=0,
                         cluster_std=0.9)
    return data


if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rt') as f:
            data = json.load(f)
    else:
        data = _fake_data()
    #print(data)

    k = kmeans(data, ['r', 'g', 'b'], 4)
    k.plot('/tmp/colors-start.png')

    for i in range(4):
        k.update()
        k.plot(f'/tmp/colors{i}.png')

