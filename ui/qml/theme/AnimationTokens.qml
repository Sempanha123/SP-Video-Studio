import QtQuick 2.15
QtObject {
    property bool reducedMotion: false
    readonly property int fast: reducedMotion ? 0 : 120
    readonly property int normal: reducedMotion ? 0 : 180
    readonly property int slow: reducedMotion ? 0 : 260
}
