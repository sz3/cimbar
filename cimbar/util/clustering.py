import json
import sys

import numpy
from sklearn.cluster import KMeans


class ClusterSituation():
    def __init__(self, data, num_clusters=4):
        if not data:
            raise Exception("what're ya doin', there's no datum points!")

        self.data = numpy.array(data)
        self.num_clusters = num_clusters
        self.kmeans = KMeans(n_clusters=num_clusters, random_state=0)
        self.kmeans.fit(self.data)
        self.labels = self.kmeans.labels_
        self.index = None

    def centers(self):
        print(self.kmeans.cluster_centers_)
        return self.kmeans.cluster_centers_

    def categorize(self, point):
        cat = self.kmeans.predict([point,])[0]
        if self.index:
            cat = self.index[cat]
        return cat

    def plot(self, filename):
        from matplotlib import pyplot

        fig = pyplot.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(self.data[:,0], self.data[:,1], self.data[:,2], c=self.kmeans.labels_)
        ax.set_ylim(ax.get_ylim()[::-1])
        pyplot.xlabel('red')
        pyplot.ylabel('green')
        fig.savefig(filename)
