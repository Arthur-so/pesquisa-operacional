# Compila o RKO (código genérico intocado em RKO_Cpp_v2.0) com o decodificador do 2BPPC
RKO = RKO_Cpp_v2.0/Program/src
CXXFLAGS = -O3 -march=native -fopenmp -std=c++20 -Wall -Wno-unused-but-set-variable -Wno-unused-variable -Wno-sign-compare
rko_bppc: src/rko_bppc.cpp src/Problem_2BPPC.h
	g++ $(CXXFLAGS) -I$(RKO) -Isrc -o $@ src/rko_bppc.cpp
clean:
	rm -f rko_bppc
