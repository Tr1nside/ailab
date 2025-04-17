#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
using namespace std;

int main() {
    // Открываем файл для чтения
    ifstream inputFile("input.txt");
    if (!inputFile.is_open()) {
        cerr << "Ошибка: файл input.txt не найден!" << endl;
        return 1;
    }

    // Открываем файл для записи результатов
    ofstream outputFile("output.txt");
    if (!outputFile.is_open()) {
        cerr << "Ошибка: не удалось создать output.txt!" << endl;
        return 1;
    }

    // Счетчики
    int charCount = 0;
    int wordCount = 0;
    string line;

    // Чтение файла построчно
    while (getline(inputFile, line)) {
        charCount += line.length(); // Символы в строке (без '\n')
        
        // Подсчет слов в строке
        istringstream iss(line);
        string word;
        while (iss >> word) {
            wordCount++;
        }
    }

    // Закрываем файлы
    inputFile.close();

    // Записываем результаты в output.txt
    outputFile << "Общее количество символов: " << charCount << endl;
    outputFile << "Общее количество слов: " << wordCount << endl;
    outputFile.close();

    // Подтверждение в консоли (опционально)
    cout << "Результаты сохранены в output.txt!" << endl;

    return 0;
}