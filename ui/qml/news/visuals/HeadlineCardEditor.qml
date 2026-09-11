import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
AppCard { property var controller; property var element: ({}); ColumnLayout { anchors.fill:parent; Text { text:"HeadlineCard"; color:Theme.colors.textPrimary; font.weight:Font.DemiBold }; Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; text:"Edit detailed geometry/style in the shared Scene Editor; News Visuals preserves provenance and layout ownership."; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } } }
