#include <iostream>
#include <vector>
#include <string>
#include <map>

using namespace std;

int main() {
    cout << "Hello, world!" << endl;
    
    vector<int> numbers = {1, 2, 3, 4, 5};
    
    for (int num : numbers) {
        cout << num << endl;
    }

    map<string, int> my_dict = {{"key1", 10}, {"key2", 20}};
    
    cout << my_dict["key1"] << endl;

    auto add = [](int a, int b) -> int {
        return a + b;
    };

    cout << add(10, 20) << endl;

    for (int i = 0; i < 5; ++i) {
        cout << i << endl;
    }

    auto square = [](int x) -> int {
        return x * x;
    };
    
    cout << square(5) << endl;

    return 0;
}
