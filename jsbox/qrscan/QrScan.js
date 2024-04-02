const appUrlPrex = {
    aliPay: "alipays://platformapi/startapp?appId=20000067&url=",
    wx: "",
    aliding: "dingtalk://dingtalkclient/page/link?url=",
};
const CACHE_KEY = "qrList";
var list = $cache.get(CACHE_KEY) || [];
const appList = [
    {
        id: "aliPay",
        app: {
            text: "支付宝",
        },
    },
    {
        id: "wx",
        app: {
            text: "微信",
        },
    },
    {
        id: "aliding",
        app: {
            text: "阿里钉",
        },
    },
];

const qrList = [
    {
        type: "add",
        label: {
            text: "添加",
        },
    },
].concat(list);

function saveCache() {
    $cache.set(CACHE_KEY, list);
}

function clearCache() {
    $cache.set(CACHE_KEY, []);
    $cache.set("idKey", 1);
}
// clearCache()
function openUrl(qrItem) {
    const latestUrl = appUrlPrex[qrItem.appId] + encodeURIComponent(qrItem.qr);
    $app.openURL(latestUrl);
}

function genrateId() {
    const idKey = "idKey";
    const id = $cache.get(idKey) || 1;
    $cache.set(idKey, id + 1);
    return id;
}

$ui.render({
    props: {
        id: "qrList",
        title: "选择二维码",
    },
    views: [
        {
            type: "list",
            props: {
                template: {
                    props: {},
                    views: [
                        {
                            type: "label",
                            props: {
                                id: "label",
                            },
                            layout: $layout.fill,
                        },
                    ],
                },
                data: qrList,
                actions: [
                    {
                        title: "delete",
                        color: $color("gray"), // default to gray
                        handler: function (sender, indexPath) {
                            const qr = list[indexPath.row - 1];
                            list = list.filter((q) => q.qrId != qr.qrId);
                            saveCache();
                        },
                    },
                ],
            },
            layout: $layout.fill,
            events: {
                swipeEnabled: function (sender, indexPath) {
                    return indexPath.row > 0;
                },
                didSelect(tableView, indexPath, title) {
                    const qr = tableView.object(indexPath);
                    if (qr.type == "add") {
                        $qrcode.scan((qrResult) => {
                            $ui.push({
                                props: {
                                    id: "appList",
                                    title: "选择APP",
                                },
                                views: [
                                    {
                                        type: "list",
                                        props: {
                                            template: {
                                                props: {},
                                                views: [
                                                    {
                                                        type: "label",
                                                        props: {
                                                            id: "app",
                                                        },
                                                        layout: $layout.fill,
                                                    },
                                                ],
                                            },
                                            data: appList,
                                        },
                                        layout: $layout.fill,
                                        events: {
                                            didSelect(tableView, indexPath, title) {
                                                const app = tableView.object(indexPath);
                                                const prefix = appUrlPrex[app.id];
                                                if (!prefix) {
                                                    $ui.alert(app.app.text + " 暂不支持");
                                                }

                                                $input.text({
                                                    type: $kbType.search,
                                                    placeholder: "输入标题",
                                                    handler: function (inputTitle) {
                                                        var qrId = genrateId();
                                                        var qrItem = {
                                                            type: "qr",
                                                            appId: app.id,
                                                            qrId: qrId,
                                                            qr: qrResult,
                                                            label: {
                                                                text: "【" + qrId + "】:" + inputTitle,
                                                            },
                                                        };
                                                        list.push(qrItem);
                                                        saveCache();
                                                        openUrl(qrItem);
                                                    },
                                                });
                                            },
                                        },
                                    },
                                ],
                            });
                        });
                    } else {
                        openUrl(qr);
                    }
                },
            },
        },
    ],
});
