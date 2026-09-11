import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { property var itemData:({})
    ColumnLayout { anchors.fill:parent
        Text { text:itemData.errorMessage ? "Error" : "No item error"; color:Theme.colors.textPrimary; font.weight:Theme.type.semibold }
        Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; text:itemData.errorMessage || "Failed items keep concise errors here. Technical details stay item-scoped so row content is not logged at INFO."; color:Theme.colors.textSecondary }
        Text { text:itemData.errorCode || ""; color:Theme.colors.textSecondary }
        Item { Layout.fillHeight:true }
    }
}
