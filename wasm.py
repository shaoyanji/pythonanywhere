# main.py
from wasmtime import Store, Module, Instance, Func, FuncType, ValType
def run():
    store = Store()
    module = Module.from_file(store.engine, 'app/static/wasm.wasm')
    hello1 = Func(store,FuncType([ValType.i32()],[]), 0)
    hello2 = Func(store,FuncType([ValType.i32(),ValType.i32()],[ValType.i32()]), 0)
    hello3 = Func(store,FuncType([ValType.i32(),ValType.i32(),ValType.i32(),ValType.i32()],[ValType.i32()]), 0)
    instance = Instance(store, module, [hello1,hello3,hello2])
    #instance.exports(store)["kc"](store)
    kc_func= instance.exports(store)["kc"]
    #kc_func= instance.exports(store)["kc"](store)
    result = kc_func(store,80,50,50)
    print("Probability of 60 has a Kelly Criteria of:", result)
#    run = instance.exports(store)["run"]
 #   run(store)

if __name__ == '__main__':
    run()
