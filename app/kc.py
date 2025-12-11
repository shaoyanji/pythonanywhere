from wasmtime import Store, Module, Instance, Func, FuncType, ValType


def run(p, re, ri):
    store = Store()
    module = Module.from_file(store.engine, "./app/static/wasm.wasm")
    hello1 = Func(store, FuncType([ValType.i32()], []), 0)
    hello2 = Func(store, FuncType([ValType.i32(), ValType.i32()], [ValType.i32()]), 0)
    hello3 = Func(
        store,
        FuncType(
            [ValType.i32(), ValType.i32(), ValType.i32(), ValType.i32()],
            [ValType.i32()],
        ),
        0,
    )
    instance = Instance(store, module, [hello1, hello3, hello2])
    kc_func = instance.exports(store)["kc"]
    result = kc_func(store, p, re, ri)
    return result


if __name__ == "__main__":
    print(run(60, 50, 50))
