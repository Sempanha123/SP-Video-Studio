import QtQuick 2.15
QtObject {
    property real scale: 1.0
    readonly property string family: "Segoe UI"
    readonly property string unicodeFallback: "Noto Sans"
    readonly property string khmerFallback: "Noto Sans Khmer"
    readonly property string thaiFallback: "Noto Sans Thai"
    function px(base) { return Math.max(9, Math.round(base * scale)) }
    readonly property int display: px(24)
    readonly property int titleLarge: px(22)
    readonly property int pageTitle: px(22)
    readonly property int title: px(18)
    readonly property int titleMedium: px(17)
    readonly property int sectionTitle: px(16)
    readonly property int heading: px(15)
    readonly property int bodyStrong: px(14)
    readonly property int body: px(14)
    readonly property int bodySmall: px(13)
    readonly property int small: px(12)
    readonly property int caption: px(12)
    readonly property int label: px(12)
    readonly property int button: px(13)
    readonly property int timeline: px(11)
    readonly property real normalLineHeight: 1.38
    readonly property real multilingualLineHeight: 1.58
    readonly property int regular: 400
    readonly property int medium: 500
    readonly property int semibold: 600
    readonly property int bold: 700
}
