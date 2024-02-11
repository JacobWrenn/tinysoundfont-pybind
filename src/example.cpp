#include <pybind11/pybind11.h>

int add(int i, int j) {
    return i + j;
}

PYBIND11_MODULE(pytinysoundfont, m) {
    m.doc() = "pybind11 example plugin";

    m.def("add", &add, "A function that adds two numbers");
}
