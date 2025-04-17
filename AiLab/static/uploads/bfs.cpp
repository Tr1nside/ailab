#include <iostream>
#include <vector>
#include <queue>
using namespace std;

const int INF = 1e9;

vector<int> bfs(vector<vector<int>> &graph, vector<int> &starts) {
    vector<int> dist(graph.size(), INF);
    queue<int> q;

    for (int start : starts) {
        dist[start] = 0;
        q.push(start);
    }
    


    while (!q.empty()) {
        int v = q.front();
        q.pop();

        for (int to : graph[v]) {
            if (dist[to] > dist[v] + 1) {
                dist[to] = dist[v] + 1;
                q.push(to);
            }
        }
    }
    
    return dist;
}

int main() {
    freopen("input.txt", "r", stdin);
    freopen("output.txt", "w", stdout);
    
    int vertexCount, edgeCount;
    cin >> vertexCount >> edgeCount;

    vector<vector<int>> graph(vertexCount);
    for (int i = 0; i < edgeCount; i++) {
        int a, b;
        cin >> a >> b;
         
        graph[a].push_back(b);
        graph[b].push_back(a);
    }

    int startCount;
    vector<int> starts;
    cin >> startCount;

    for (int i = 0; i < startCount; i++) {
        int a;
        cin >> a;
        starts.push_back(a);
    }

    vector<int> dist = bfs(graph, starts);

    for(int d : dist) {
        if (d != INF) {
            cout << d << " ";
        } else {
            cout << "X ";
        }
     }
}